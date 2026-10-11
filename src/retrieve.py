"""의회별 하이브리드 검색: BM25(bm25s) + bge-m3 밀집 검색을 Reciprocal Rank Fusion으로 합친다.

본보기와 근거:
  - RRF: Cormack, Clarke & Büttcher (2009) "Reciprocal Rank Fusion outperforms Condorcet and individual rank
    learning methods". score(d) = Σ_r 1 / (k + rank_r(d)), k = 60. LlamaIndex의 QueryFusionRetriever와
    Haystack의 DocumentJoiner(reciprocal_rank_fusion)도 같은 식을 쓴다.
  - 질의 확장: 이슈 이름 질의에 더해, 이미 확인된 근거 문단(관련 점수 상위)의 평균 벡터를 두 번째 밀집 질의로 쓴다
    (Rocchio 유사 적합성 피드백, Rocchio 1971; 밀집 검색에서의 PRF는 Li et al. 2023 "Pseudo Relevance Feedback
    with Deep Language Models and Dense Retrievers" 참고). 별칭이 없는 바꿔 쓴 언급을 찾으려는 것이다.
  - 찾은 문단은 events.relevance()의 교차 인코더 점수로 다시 판정한다(검색은 넓게, 판정은 정확히).

색인은 scripts/09_build_index.py가 의회별로 만든다. 밀집 벡터는 mmap으로 읽어 메모리를 적게 쓴다.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "data" / "index"
COUNCILS = ["서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종", "경기",
            "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주"]
KEEP_TAGS = ("NNG", "NNP", "SL", "SH", "XR", "VV", "VA")
RRF_K = 60
_kiwi = None


def bm25_tokens(texts: list[str]) -> list[list[str]]:
    """BM25용 토큰: Kiwi 형태소 중 명사·고유명사·어근·용언 어간·외국어·한자. 띄어쓰기가 달라도 같은 토큰이 된다."""
    global _kiwi
    if _kiwi is None:
        from kiwipiepy import Kiwi
        _kiwi = Kiwi(num_workers=4)
    return [[t.form.lower() for t in r if t.tag in KEEP_TAGS] or ["_"] for r in _kiwi.tokenize(texts)]


def index_ready(councils=COUNCILS) -> bool:
    """모든 의회의 BM25와 밀집 색인이 있는가."""
    return all((INDEX / c / "bm25").exists() and (INDEX / c / "dense.npy").exists() for c in councils)


def rrf(rankings: list[list[int]], k: int = RRF_K) -> dict[int, float]:
    """여러 순위 목록(행 번호, 앞일수록 높음)을 RRF 점수로 합친다."""
    s: dict[int, float] = {}
    for rk in rankings:
        for r, i in enumerate(rk, 1):
            s[i] = s.get(i, 0.0) + 1.0 / (k + r)
    return s


class CouncilIndex:
    """의회 하나의 BM25 + 밀집 색인."""

    def __init__(self, council: str):
        import bm25s
        d = INDEX / council
        self.council = council
        self.meta = pd.read_parquet(d / "meta.parquet")
        self.bm25 = bm25s.BM25.load(str(d / "bm25"), mmap=True)
        self.dense = np.load(d / "dense.npy", mmap_mode="r")

    def bm25_top(self, query_tokens: list[list[str]], k: int) -> list[list[int]]:
        res, _ = self.bm25.retrieve(query_tokens, k=min(k, len(self.meta)), show_progress=False)
        return [list(map(int, r)) for r in res]

    def dense_top(self, qvecs: np.ndarray, k: int, chunk: int = 50_000) -> list[list[int]]:
        """질의 여러 개를 한 번에: 벡터를 덩어리로 읽어 내적하고 질의마다 상위 k개를 남긴다."""
        q = qvecs.astype(np.float32)
        best_s = np.full((len(q), 0), -np.inf, dtype=np.float32)
        best_i = np.zeros((len(q), 0), dtype=np.int64)
        for a in range(0, len(self.dense), chunk):
            s = np.asarray(self.dense[a: a + chunk], dtype=np.float32) @ q.T          # (chunk, nq)
            kk = min(k, s.shape[0])
            idx = np.argpartition(-s, kk - 1, axis=0)[:kk].T                          # (nq, kk)
            sc = np.take_along_axis(s.T, idx, axis=1)
            best_s = np.concatenate([best_s, sc], axis=1)
            best_i = np.concatenate([best_i, idx + a], axis=1)
            if best_s.shape[1] > k:
                keep = np.argpartition(-best_s, k - 1, axis=1)[:, :k]
                best_s = np.take_along_axis(best_s, keep, axis=1)
                best_i = np.take_along_axis(best_i, keep, axis=1)
        order = np.argsort(-best_s, axis=1)
        return np.take_along_axis(best_i, order, axis=1).tolist()


def hybrid_search(queries: dict, k: int = 30, k_each: int = 100, councils=COUNCILS, encoder=None) -> pd.DataFrame:
    """queries: {qid: {"text": 이슈 정의 문장, "tokens": [...BM25 토큰], "vecs": [추가 밀집 질의 벡터, ...]}}.
    의회마다 BM25 상위 k_each, 밀집 질의마다 상위 k_each를 RRF로 합쳐 상위 k개를 돌려준다.
    돌려주는 표: qid, council, pid, doc_id, date, rrf, ranks(어느 검색에서 몇 위였는지)."""
    qids = list(queries)
    if encoder is not None:
        tv = encoder.encode([queries[q]["text"] for q in qids], normalize_embeddings=True, convert_to_numpy=True)
    rows = []
    for c in councils:
        if not (INDEX / c / "dense.npy").exists() or not (INDEX / c / "bm25").exists():
            continue
        ix = CouncilIndex(c)
        b_top = ix.bm25_top([queries[q]["tokens"] for q in qids], k_each)
        vec_list, owner = [], []
        for j, q in enumerate(qids):
            if encoder is not None:
                vec_list.append(tv[j]); owner.append((j, "dense_name"))
            for v in queries[q].get("vecs", []):
                vec_list.append(v); owner.append((j, "dense_prf"))
        d_top = ix.dense_top(np.stack(vec_list), k_each) if vec_list else []
        per_q = {j: {"bm25": b_top[j]} for j in range(len(qids))}
        for (j, name), top in zip(owner, d_top):
            per_q[j][name] = top
        for j, q in enumerate(qids):
            ranked = per_q[j]
            fused = sorted(rrf(list(ranked.values())).items(), key=lambda x: -x[1])[:k]
            for i, s in fused:
                m = ix.meta.iloc[i]
                where = {name: rk.index(i) + 1 for name, rk in ranked.items() if i in rk}
                rows.append({"qid": q, "council": c, "pid": m.pid, "doc_id": m.doc_id, "date": m.date, "rrf": s,
                             "ranks": where})
        del ix
    return pd.DataFrame(rows)
