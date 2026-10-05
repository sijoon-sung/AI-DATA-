"""6단계: 사람이 검수할 표본(라벨링 풀) 추출.

과제마다 약지도 라벨별로 층을 나눠 뽑고, 의회가 고르게 섞이도록 의회 단위로 돌아가며 고른다.
출력: data/labels/pool_{task}.jsonl  (한 줄 = 문단 하나, 앞뒤 문단을 맥락으로 함께 담음)
"""
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.weak_labels import find_regions  # noqa: E402

P = ROOT / "data" / "processed"
OUT = ROOT / "data" / "labels"
OUT.mkdir(parents=True, exist_ok=True)
SEED = 20261006

w = pd.read_parquet(P / "passages_weak.parquet")
pas = pd.read_parquet(P / "passages.parquet", columns=["pid", "doc_id", "utt_idx", "part", "role", "name", "start", "end", "text"])
docs = pd.read_parquet(P / "docs.parquet", columns=["doc_id", "mints_nm", "committee", "keep"])
docs = docs[docs.keep]


def stratified(df, plan, by="council_short"):
    """plan = {약라벨값(None은 '보류'): 개수}. 의회별로 돌아가며 골라 편중을 줄인다."""
    picks = []
    for lab, n in plan.items():
        sub = df[df["wlab"].isna()] if lab is None else df[df["wlab"] == lab]
        sub = sub.sample(frac=1, random_state=SEED)
        sub = sub.assign(rr=sub.groupby(by).cumcount()).sort_values("rr")
        picks.append(sub.head(n))
    return pd.concat(picks).sample(frac=1, random_state=SEED)


long_ = w[w.n_chars >= 30]
pools = {
    "ref": stratified(long_[long_.regions != ""].assign(wlab=lambda d: d.w_ref),
                      {"POLICY_REF": 200, "COMPARE": 100, "COOP": 100, "OTHER": 100, None: 100}),
    "proc": stratified(w[w.n_chars >= 10].assign(wlab=lambda d: d.w_proc),
                       {"PROC": 120, "SUB": 120, None: 160}),
    "topdown": stratified(long_[long_.w_proc != "PROC"].assign(wlab=lambda d: d.w_topdown),
                          {"TOPDOWN": 200, None: 200}),
}

need = set().union(*[set(p.pid) for p in pools.values()])
pas = pas.set_index("pid")
meta = docs.set_index("doc_id")
for task, pool in pools.items():
    with open(OUT / f"pool_{task}.jsonl", "w", encoding="utf-8") as f:
        for r in pool.itertuples(index=False):
            p = pas.loc[r.pid]
            # 같은 회의록에서 바로 앞뒤 발언의 첫 문단을 맥락으로 붙인다
            ctx = {}
            for k, d in (("prev", -1), ("next", 1)):
                q = f"{p.doc_id}_{p.utt_idx + d}_0"
                if q in pas.index:
                    c = pas.loc[q]
                    ctx[k] = {"speaker": f"{c['role']} {c['name']}", "text": c.text[:300]}
            m = meta.loc[p.doc_id]
            regions = find_regions(p.text, r.council_short) if task == "ref" else []
            f.write(json.dumps({
                "task": task, "pid": r.pid, "weak": r.wlab,
                "council": r.council_short, "date": str(r.date)[:10],
                "mints_nm": m.mints_nm, "committee": m.committee,
                "speaker": f"{p['role']} {p['name']}", "doc_id": p.doc_id, "start": int(p.start), "end": int(p.end),
                "text": p.text, "regions": [[k, s, e] for k, s, e in regions], "context": ctx,
            }, ensure_ascii=False) + "\n")
    print(task, len(pool), pool["wlab"].value_counts(dropna=False).to_dict(),
          "| 의회 수", pool.council_short.nunique())
