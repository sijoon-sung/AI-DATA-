"""12단계: 새 파이프라인을 검증할 정답셋 검수 표본을 만든다(검수는 src/labeler/server.py로 사람이 한다).

과제
  rel  (이슈, 문단) 관련성: 이 문단이 이 이슈를 중심으로 다루는가 / 지나가며 언급하는가 / 무관·동명이의인가.
       층: 출처(핵심 별칭, 넓은 별칭, 의미 검색) × 관련 점수 구간(<0.2, 0.2~0.5, 0.5~0.8, ≥0.8),
       그리고 (이슈, 의회)별 '확인된 최초 관측' 문단. 층마다 무작위로 뽑는다(층별 표본 비율은 _w에 둔다).
  e1   다른 의회 정책 언급: 규칙 후보 전부(NLI로 걸러진 것과 남은 것 모두). NLI의 정밀도와 재현율을 함께 잴 수 있다.
모델 점수와 층 정보는 '_'로 시작하는 열에 두고 검수 화면에는 보내지 않는다(판단이 모델 쪽으로 끌리지 않게).
이 표본으로 나중에 Prediction-Powered Inference(Angelopoulos et al. 2023)로 정밀도의 신뢰구간을 낸다(src/ppi.py).
출력: data/labels/pool_rel.jsonl, data/labels/pool_e1.jsonl  (회의록 원문이 들어 있어 저장소에 올리지 않는다)
실행: python scripts/12_eval_pools.py
"""
import json
import re
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src import cards, issues, nli  # noqa: E402

P = ROOT / "data" / "processed"
L = ROOT / "data" / "labels"
L.mkdir(parents=True, exist_ok=True)
rng = np.random.default_rng(20261011)

ev = pd.read_parquet(P / "events.parquet")
iss = pd.read_parquet(P / "issues.parquet", columns=["issue_id", "title", "query", "aliases"])
info = iss.set_index("issue_id")
if "source" not in ev:
    ev["source"] = "alias"
ev["origin"] = np.where(ev.source == "semantic", "semantic", np.where(ev.core, "core", "broad"))
ev["bin"] = pd.cut(ev.rel, [-0.01, 0.2, 0.5, 0.8, 1.01], labels=["<0.2", "0.2-0.5", "0.5-0.8", ">=0.8"]).astype(str)


def item(r, task, extra=None):
    alias = "|".join(issues.alias_regex(a) for a in info.loc[r.issue_id, "aliases"])
    regions = [["alias", m.start(), m.end()] for m in re.finditer(alias, r.text)] if alias else []
    d = {"pid": f"{r.issue_id}|{r.pid}", "task": task, "issue": info.loc[r.issue_id, "title"],
         "issue_def": info.loc[r.issue_id, "query"], "council": r.council_short, "date": str(r.date.date()),
         "mints_nm": r.mints_nm, "speaker": r.role or "", "text": r.text, "regions": regions,
         "_issue_id": r.issue_id, "_rel": round(float(r.rel), 4), "_origin": r.origin, "_bin": r.bin}
    d.update(extra or {})
    return d


# ---------------------------------------------------------------- rel
parts = []
for (o, b), g in ev.groupby(["origin", "bin"]):
    n = min(len(g), 30 if o != "core" else 25)
    if n:
        parts.append(g.sample(n, random_state=int(rng.integers(1e9))).assign(_stratum=f"{o}/{b}", _N=len(g)))
first = (ev[ev.rel >= cards.REL_TAU].sort_values("date").groupby(["issue_id", "council_short"]).head(1))
parts.append(first.sample(min(80, len(first)), random_state=1).assign(_stratum="first_confirmed", _N=len(first)))
rel = pd.concat(parts).drop_duplicates(["issue_id", "pid"]).sample(frac=1, random_state=2)
with open(L / "pool_rel.jsonl", "w", encoding="utf-8") as f:
    for r in rel.itertuples():
        f.write(json.dumps(item(r, "rel", {"_stratum": r._stratum, "_N": int(r._N)}), ensure_ascii=False) + "\n")
print("rel 표본", len(rel), rel._stratum.value_counts().to_dict())

# ---------------------------------------------------------------- e1
use = ev[ev.core | (ev.rel >= cards.REL_TAU)]
rows = []
for r in iss.itertuples():
    alias = "|".join(issues.alias_regex(a) for a in r.aliases)
    for c in cards.reference_candidates(use[use.issue_id == r.issue_id], alias, nli):
        rows.append({"pid": f"{r.issue_id}|{c['pid']}|{c['to']}", "task": "e1", "issue": r.title, "issue_def": r.query,
                     "council": c["council"], "date": c["date"], "mints_nm": c["doc"], "speaker": c.get("role") or "",
                     "text": c["sentence"], "regions": [["to", c["span"][0], c["span"][1]]], "target": c["to"],
                     "_issue_id": r.issue_id, "_nli": c["nli"], "_accepted": c["nli"] >= cards.NLI_TAU})
with open(L / "pool_e1.jsonl", "w", encoding="utf-8") as f:
    for d in rng.permutation(rows):
        f.write(json.dumps(d, ensure_ascii=False) + "\n")
print("e1 표본", len(rows), "NLI 통과", sum(d["_accepted"] for d in rows))
