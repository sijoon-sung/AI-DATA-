"""10단계 실험(RQ1): 일반적인 top-k RAG 검색은 '의회별 최초 관측'을 얼마나 놓치는가.

비교하는 검색 방식(모두 같은 bge-m3 밀집 색인과 같은 관련 판정기 bge-reranker-v2-m3를 쓴다):
  global@K        이슈 이름으로 전체 회의록에서 상위 K개 (보통의 RAG, K = 10, 50, 200)
  council@k       의회마다 상위 k개 (의회로 층을 나눈 검색, k = 10)
  council-month@k (의회 × 월)마다 상위 k개 (시간까지 층을 나눈 검색, k = 3)
  ours            별칭 전수 검색 + 하이브리드 검색 + 관련 판정 (08단계의 사건표)
기준(은표준): 08단계 사건표에서 관련 점수 0.5 이상인 문단으로 정한 (이슈, 의회)별 확인된 최초 관측일.
  사람 정답이 아니라 우리 시스템의 결과이므로, 이 실험은 "전수 추출 대비 top-k 검색의 재현율"을 잰다.
지표: 의회 재현율(기준에 있는 의회 중 찾은 비율), 첫 관측일 일치율, 늦게 찾은 경우의 지연 일수 중앙값,
      이슈 전체의 최초 관측(가장 이른 의회·날짜)을 맞힌 비율.

동기: 상위 k 검색은 질의와 가장 비슷한 문단을 고를 뿐 가장 이른 문단을 고르지 않는다. 시간 순서나 집계를 묻는
질문에서 표준 RAG가 약하다는 보고가 있다(docs/04 6절, reports/ 참고).
출력: results/rag_baseline.json, results/rag_baseline.csv
실행: python scripts/10_rag_baseline.py  (색인: scripts/09_build_index.py, 사건표: scripts/08_issue_cards.py)
"""
import json
import sys
import time
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import numpy as np
import pandas as pd
import pyarrow.dataset as ds

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src import events, retrieve  # noqa: E402

P = ROOT / "data" / "processed"
TAU = 0.5
t0 = time.time()


def log(m):
    print(f"[{time.time() - t0:6.0f}초] {m}", flush=True)


ev = pd.read_parquet(P / "events.parquet", columns=["issue_id", "pid", "council_short", "date", "rel"])
iss = pd.read_parquet(P / "issues.parquet", columns=["issue_id", "kind", "title", "query"])
ref = ev[ev.rel >= TAU].groupby(["issue_id", "council_short"]).date.min().rename("ref").reset_index()
known = {(a, b): r for a, b, r in zip(ev.issue_id, ev.pid, ev.rel)}

import torch  # noqa: E402
from sentence_transformers import SentenceTransformer  # noqa: E402

enc = SentenceTransformer("BAAI/bge-m3", device="cuda" if torch.cuda.is_available() else "cpu",
                          model_kwargs={"torch_dtype": torch.float16} if torch.cuda.is_available() else {})
qids = list(iss.issue_id)
Q = enc.encode(list(iss["query"]), normalize_embeddings=True, convert_to_numpy=True).astype(np.float32)
del enc
torch.cuda.empty_cache()

# 의회마다 전체 점수를 계산해 방식별 후보를 모은다
glob_parts, picks = [], {"council@10": [], "council-month@3": []}
for c in retrieve.COUNCILS:
    meta = pd.read_parquet(retrieve.INDEX / c / "meta.parquet")
    dense = np.load(retrieve.INDEX / c / "dense.npy", mmap_mode="r")
    S = np.concatenate([np.asarray(dense[a: a + 50_000], dtype=np.float32) @ Q.T for a in range(0, len(dense), 50_000)])
    month = pd.to_datetime(meta.date).dt.to_period("M").astype(str).to_numpy()
    for j, q in enumerate(qids):
        s = S[:, j]
        top = np.argpartition(-s, 199)[:200]
        glob_parts.append(pd.DataFrame({"qid": q, "pid": meta.pid.to_numpy()[top], "score": s[top], "council": c,
                                        "date": meta.date.to_numpy()[top]}))
        t10 = top[np.argsort(-s[top])][:10]
        picks["council@10"].append(pd.DataFrame({"qid": q, "pid": meta.pid.to_numpy()[t10], "council": c, "date": meta.date.to_numpy()[t10]}))
        df = pd.DataFrame({"i": np.arange(len(s)), "s": s, "m": month})
        mt = df.sort_values("s", ascending=False).groupby("m").head(3).i.to_numpy()
        picks["council-month@3"].append(pd.DataFrame({"qid": q, "pid": meta.pid.to_numpy()[mt], "council": c, "date": meta.date.to_numpy()[mt]}))
    log(f"{c}: 문단 {len(meta):,}개 점수 계산")
g = pd.concat(glob_parts).sort_values(["qid", "score"], ascending=[True, False])
for K in (10, 50, 200):
    picks[f"global@{K}"] = [g.groupby("qid").head(K)[["qid", "pid", "council", "date"]]]
picks = {k: pd.concat(v, ignore_index=True) for k, v in picks.items()}

# 판정이 없는 (이슈, 문단)만 교차 인코더로 점수를 매긴다
allp = pd.concat(picks.values()).drop_duplicates(["qid", "pid"])
need = allp[[(q, x) not in known for q, x in zip(allp.qid, allp.pid)]]
log(f"검색 결과 {len(allp):,}쌍, 새로 판정할 쌍 {len(need):,}개")
if len(need):
    tbl = ds.dataset(P / "passages.parquet").to_table(columns=["pid", "text"], filter=ds.field("pid").isin(list(need.pid.unique())))
    nd = need.merge(tbl.to_pandas(), on="pid").rename(columns={"qid": "issue_id"})
    nd["rel"] = events.relevance(nd, dict(zip(iss.issue_id, iss["query"]))).values
    known.update({(a, b): r for a, b, r in zip(nd.issue_id, nd.pid, nd.rel)})


def evaluate(found: pd.DataFrame) -> dict:
    f = found.assign(rel=[known.get((q, x), 0.0) for q, x in zip(found.qid, found.pid)])
    f = f[f.rel >= TAU].groupby(["qid", "council"]).date.min().rename("got").reset_index()
    m = ref.merge(f, left_on=["issue_id", "council_short"], right_on=["qid", "council"], how="left")
    hit = m.got.notna()
    delay = (pd.to_datetime(m.got[hit]) - pd.to_datetime(m.ref[hit])).dt.days
    first = ref.loc[ref.groupby("issue_id").ref.idxmin()]
    fm = first.merge(f, left_on=["issue_id", "council_short"], right_on=["qid", "council"], how="left")
    return {"council_recall": round(float(hit.mean()), 3), "first_date_exact": round(float((delay == 0).sum() / len(m)), 3),
            "median_delay_days_when_found": float(delay.median()) if len(delay) else None,
            "issue_first_exact": round(float((fm.got == fm.ref).mean()), 3), "n_pairs": int(len(m)),
            "retrieved": int(len(found))}


res = {name: evaluate(df) for name, df in picks.items()}
ours = ev[ev.rel >= TAU].rename(columns={"issue_id": "qid", "council_short": "council"})[["qid", "pid", "council", "date"]]
res["ours (기준)"] = evaluate(ours)
for k, v in res.items():
    log(f"{k:18} {v}")
(ROOT / "results").mkdir(exist_ok=True)
json.dump({"tau": TAU, "reference": "08단계 사건표의 관련 점수 0.5 이상 문단(은표준)", "results": res},
          open(ROOT / "results" / "rag_baseline.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
pd.DataFrame(res).T.to_csv(ROOT / "results" / "rag_baseline.csv", encoding="utf-8-sig")
log("완료")
