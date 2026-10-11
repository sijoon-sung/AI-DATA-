"""정책 카탈로그(내용부터 묶기): 문단을 의미로 군집하고, LLM이 군집마다 정책 주제와 의회별 정책 이름을 붙인다.

이름부터 찾는 방식(discover.py)은 정책 브랜드가 지어낸 말이라 실패했다(탐나는전·기후동행카드·땡겨요를 형태소 분석기가
명사로 보지 못함, 10/11 기록). 그래서 순서를 바꾼다. 내용이 같으면(대중교통비 정액·환급) 이름이 달라도(기후동행카드,
동백패스, 이응패스) 같은 군집에 모이고, 이름은 군집 안에서 의회별로 뽑는다.

  fit       의회별 밀집 벡터(scripts/09)에서 표본을 뽑아 구면 k-평균(faiss)으로 주제 중심을 만든다
  assign    모든 문단을 가장 가까운 중심에 배정한다(코사인 유사도도 저장). 새 회의록도 같은 함수로 배정한다
  describe  주제마다 크기, 의회 분포, 의회별 대표 문단(중심에 가장 가까운 것)을 뽑는다
  label     로컬 LLM(Qwen2.5-7B)이 대표 문단을 읽고 정책 주제인지, 주제 이름·정의, 의회별 정책 이름을 JSON으로 낸다.
            LLM이 낸 이름은 그 의회의 대표 문단에 실제로 있는지 글자로 확인한다(없으면 버린다)
  family    정책 주제의 정의를 bge-m3로 묻어 가까운 주제를 하나의 정책 가족으로 합친다
본보기: BERTopic(Grootendorst 2022; 임베딩 군집 + 주제 표현, LLM 표현과 온라인 갱신 지원),
        GraphRAG/LightRAG의 증분 갱신(새 자료만 처리해 기존 구조에 더함).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
INDEX = ROOT / "data" / "index"
CAT = ROOT / "data" / "catalog"
COUNCILS = ["서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종", "경기",
            "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주"]


def ready_councils(councils=COUNCILS):
    return [c for c in councils if (INDEX / c / "dense.npy").exists()]


def _meta(c, until=None, since=None):
    m = pd.read_parquet(INDEX / c / "meta.parquet")
    m["row"] = np.arange(len(m))
    if until:
        m = m[pd.to_datetime(m.date) <= pd.Timestamp(until)]
    if since:
        m = m[pd.to_datetime(m.date) >= pd.Timestamp(since)]
    return m


def fit(k=800, per_council=12000, until=None, seed=0, councils=None):
    """표본으로 주제 중심을 만든다. 돌려주는 값: (k, 1024) float32, 정규화된 중심."""
    import faiss
    rng = np.random.default_rng(seed)
    xs = []
    for c in councils or ready_councils():
        m = _meta(c, until=until)
        rows = np.sort(rng.choice(m.row.to_numpy(), size=min(per_council, len(m)), replace=False))
        d = np.load(INDEX / c / "dense.npy", mmap_mode="r")
        xs.append(np.asarray(d[rows], dtype=np.float32))
    x = np.concatenate(xs)
    km = faiss.Kmeans(x.shape[1], k, niter=25, seed=seed, spherical=True, verbose=False)
    km.train(x)
    cen = km.centroids.astype(np.float32)
    return cen / np.linalg.norm(cen, axis=1, keepdims=True)


def assign(c, cen, since=None, until=None, chunk=50_000) -> pd.DataFrame:
    """의회 하나의 문단을 가장 가까운 주제에 배정한다. 돌려주는 표: pid, doc_id, date, topic, sim."""
    m = _meta(c, until=until, since=since)
    d = np.load(INDEX / c / "dense.npy", mmap_mode="r")
    rows = m.row.to_numpy()
    tp, sm = np.empty(len(rows), np.int32), np.empty(len(rows), np.float32)
    for a in range(0, len(rows), chunk):
        s = np.asarray(d[rows[a: a + chunk]], dtype=np.float32) @ cen.T
        tp[a: a + chunk] = s.argmax(1)
        sm[a: a + chunk] = s.max(1)
    return pd.DataFrame({"pid": m.pid.to_numpy(), "doc_id": m.doc_id.to_numpy(), "date": m.date.to_numpy(),
                         "council": c, "topic": tp, "sim": sm})


def describe(asg: pd.DataFrame, per_council=1, max_councils=12, top_overall=3) -> pd.DataFrame:
    """주제마다 크기·의회 분포·대표 문단 pid. 대표: 문단이 많은 의회부터 의회마다 중심에 가장 가까운 문단 + 전체 상위."""
    rows = []
    for t, g in asg.groupby("topic"):
        dist = g.council.value_counts()
        reps = []
        for c in dist.index[:max_councils]:
            reps += list(g[g.council == c].nlargest(per_council, "sim").pid)
        reps += [p for p in g.nlargest(top_overall + len(reps), "sim").pid if p not in reps][:top_overall]
        rows.append({"topic": int(t), "size": len(g), "n_councils": int(dist.size),
                     "top_council_share": round(float(dist.iloc[0] / len(g)), 3),
                     "councils": json.dumps(dist.to_dict(), ensure_ascii=False), "reps": reps,
                     "first_date": str(pd.to_datetime(g.date).min().date())})
    return pd.DataFrame(rows)


LABEL_SYSTEM = (
    "너는 한국 광역의회 회의록을 분석해 정책 주제를 정리하는 도우미다. 주어진 회의록 문단만 근거로 쓴다. "
    "문단들이 공통으로 다루는 것이 주민에게 제공되는 정책·사업·제도(예: 교통비 지원, 지역화폐, 청년 수당, 공공배달앱)이면 "
    "정책주제를 true로 하고, 회의 진행, 예산 절차 일반, 인사, 의례, 여러 주제가 섞인 경우면 false로 한다. "
    "의회별 정책이름에는 그 의회 문단에 실제로 적힌 고유한 사업·제도 이름만 문단의 표기 그대로 넣는다(일반 명사는 넣지 않는다). "
    "반드시 JSON 하나만 출력한다.")
LABEL_SCHEMA = ('{"정책주제": true/false, "주제": "10자 안팎의 주제 이름", "정의": "이 정책이 누구에게 무엇을 하는지 한 문장", '
                '"분야": "교통/복지/경제/교육/환경/안전/문화/행정/기타 중 하나", '
                '"의회별_정책이름": [{"의회": "부산", "이름": "동백패스"}], "국가사업": ["국가가 운영하는 같은 목적의 사업 이름"]}')


def label_prompt(reps: pd.DataFrame, width=220) -> list[dict]:
    lines = [f"[{r.council}] {r.text[:width].strip()}" for r in reps.itertuples()]
    user = "회의록 문단:\n" + "\n".join(lines) + f"\n\n다음 형식의 JSON으로 답하라:\n{LABEL_SCHEMA}"
    return [{"role": "system", "content": LABEL_SYSTEM}, {"role": "user", "content": user}]


def parse_label(text: str) -> dict | None:
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def verify_names(lab: dict, reps: pd.DataFrame) -> dict:
    """LLM이 낸 의회별 정책 이름이 그 의회 대표 문단에 글자로 있는지 확인한다(띄어쓰기 무시). 없으면 버린다."""
    by = {c: re.sub(r"\s", "", " ".join(g.text)) for c, g in reps.groupby("council")}
    keep, drop = [], []
    for x in lab.get("의회별_정책이름") or []:
        name, c = str(x.get("이름", "")).strip(), str(x.get("의회", "")).strip()
        if name and re.sub(r"\s", "", name) in by.get(c, ""):
            keep.append({"의회": c, "이름": name})
        else:
            drop.append({"의회": c, "이름": name})
    lab["의회별_정책이름"], lab["버린_이름"] = keep, drop
    return lab
