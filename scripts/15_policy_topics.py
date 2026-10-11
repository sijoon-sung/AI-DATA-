"""15단계: 정책 카탈로그 — 이름이 아니라 내용으로 지역 정책을 묶는다(src/catalog/topics.py).

선행: scripts/09_build_index.py --part dense (의회별 밀집 벡터). 끝난 의회만 쓴다.
단계 (순서대로, 각각 따로 돌릴 수 있다)
  python scripts/15_policy_topics.py fit      [--k 800] [--per-council 12000] [--until 2024-12-31]
  python scripts/15_policy_topics.py assign   [--since 2025-01-01]   # 문단을 주제에 배정(새 회의록은 --since)
  python scripts/15_policy_topics.py describe                        # 주제별 크기·의회 분포·대표 문단
  python scripts/15_policy_topics.py label    [--limit 0]            # 로컬 Qwen이 주제 이름·정의·의회별 정책 이름(GPU, 주제당 약 10초)
  python scripts/15_policy_topics.py family   [--tau 0.85]           # 정의가 가까운 정책 주제를 정책 가족으로 합침
  python scripts/15_policy_topics.py eval                            # eval/gold_families.json으로 평가(시스템은 이 파일을 읽지 않음)
갱신 실험: fit --until 2024-12-31 → assign → describe → label → family → assign --since 2025-01-01 → eval
출력: data/catalog/topics/ (centroids.npy, assign_<의회>.parquet, topics.parquet, labels.jsonl, families.parquet, eval.json)
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import numpy as np
import pandas as pd
import pyarrow.compute as pc
import pyarrow.dataset as ds
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.catalog import topics as T  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("step", choices=["fit", "assign", "describe", "label", "family", "eval"])
ap.add_argument("--k", type=int, default=800)
ap.add_argument("--per-council", type=int, default=12000)
ap.add_argument("--until", default=None)
ap.add_argument("--since", default=None)
ap.add_argument("--limit", type=int, default=0)
ap.add_argument("--tau", type=float, default=0.85)
args = ap.parse_args()
OUT = T.CAT / "topics"
OUT.mkdir(parents=True, exist_ok=True)
P = ROOT / "data" / "processed"
t0 = time.time()


def log(m):
    print(f"[{time.time() - t0:6.0f}초] {m}", flush=True)


def load_assign():
    fs = sorted(OUT.glob("assign_*.parquet"))
    return pd.concat([pd.read_parquet(f) for f in fs], ignore_index=True)


def texts_for(pids):
    tbl = ds.dataset(P / "passages.parquet").to_table(columns=["pid", "text"], filter=ds.field("pid").isin(list(pids)))
    return dict(zip(tbl.column("pid").to_pylist(), tbl.column("text").to_pylist()))


if args.step == "fit":
    cs = T.ready_councils()
    log(f"밀집 색인이 있는 의회 {len(cs)}곳: {', '.join(cs)}")
    for old in [*OUT.glob("assign_*.parquet"), OUT / "topics.parquet", OUT / "labels.jsonl", OUT / "families.parquet"]:
        old.unlink(missing_ok=True)   # 주제 번호가 바뀌므로 이전 배정·이름·가족을 지운다
    cen = T.fit(k=args.k, per_council=args.per_council, until=args.until, councils=cs)
    np.save(OUT / "centroids.npy", cen)
    json.dump({"k": args.k, "per_council": args.per_council, "until": args.until, "councils": cs},
              open(OUT / "fit.json", "w", encoding="utf-8"), ensure_ascii=False)
    log(f"주제 중심 {cen.shape} 저장")

elif args.step == "assign":
    cen = np.load(OUT / "centroids.npy")
    for c in T.ready_councils():
        a = T.assign(c, cen, since=args.since, until=args.until)
        path = OUT / f"assign_{c}.parquet"
        if args.since and path.exists():   # 새 회의록: 기존 배정에 더한다(같은 pid는 새 값으로)
            old = pd.read_parquet(path)
            a = pd.concat([old[~old.pid.isin(a.pid)], a], ignore_index=True)
        a.to_parquet(path, index=False)
        log(f"{c}: 문단 {len(a):,}개 배정, 유사도 중앙값 {a.sim.median():.3f}")

elif args.step == "describe":
    d = T.describe(load_assign())
    d.to_parquet(OUT / "topics.parquet", index=False)
    log(f"주제 {len(d)}개, 크기 중앙값 {int(d['size'].median())}, 여러 의회(≥5)에 걸친 주제 {(d.n_councils >= 5).sum()}개")

elif args.step == "label":
    from src.qa import load_llm
    d = pd.read_parquet(OUT / "topics.parquet").sort_values("size", ascending=False)
    done = set()
    path = OUT / "labels.jsonl"
    if path.exists():
        done = {json.loads(x)["topic"] for x in path.read_text(encoding="utf-8").splitlines() if x.strip()}
    todo = d[~d.topic.isin(done)]
    if args.limit:
        todo = todo.head(args.limit)
    asg = load_assign()
    rep_pids = {p for r in todo.itertuples() for p in r.reps}
    tx = texts_for(rep_pids)
    meta = asg.set_index("pid").loc[list(rep_pids), ["council"]]
    llm = load_llm(n_ctx=6144)
    log(f"주제 {len(todo)}개 이름 붙이기 시작(이미 {len(done)}개)")
    with open(path, "a", encoding="utf-8") as f:
        for i, r in enumerate(todo.itertuples(), 1):
            reps = pd.DataFrame({"pid": list(r.reps)})
            reps["council"] = reps.pid.map(meta.council)
            reps["text"] = reps.pid.map(tx).fillna("")
            out = llm.create_chat_completion(messages=T.label_prompt(reps), temperature=0.0, max_tokens=400,
                                             response_format={"type": "json_object"})
            lab = T.parse_label(out["choices"][0]["message"]["content"]) or {"정책주제": None, "오류": "JSON 해석 실패"}
            lab = T.verify_names(lab, reps)
            lab.update(topic=int(r.topic), size=int(r.size), n_councils=int(r.n_councils))
            f.write(json.dumps(lab, ensure_ascii=False) + "\n")
            f.flush()
            if i % 20 == 0:
                log(f"{i}/{len(todo)}")
    log("완료")

elif args.step == "family":
    from sentence_transformers import SentenceTransformer
    from sklearn.cluster import AgglomerativeClustering
    labs = [json.loads(x) for x in (OUT / "labels.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    pol = [x for x in labs if x.get("정책주제")]
    enc = SentenceTransformer("BAAI/bge-m3")
    v = enc.encode([f'{x.get("주제", "")}: {x.get("정의", "")}' for x in pol], normalize_embeddings=True)
    cl = AgglomerativeClustering(n_clusters=None, metric="cosine", linkage="average",
                                 distance_threshold=1 - args.tau).fit(v).labels_
    rows = []
    for x, f in zip(pol, cl):
        rows.append({"topic": x["topic"], "family": int(f), "주제": x.get("주제"), "정의": x.get("정의"), "분야": x.get("분야"),
                     "이름": json.dumps(x.get("의회별_정책이름", []), ensure_ascii=False), "size": x["size"]})
    fam = pd.DataFrame(rows)
    name = fam.sort_values("size", ascending=False).drop_duplicates("family").set_index("family")["주제"]
    fam["family_name"] = fam.family.map(name)
    fam.to_parquet(OUT / "families.parquet", index=False)
    log(f"정책 주제 {len(pol)}개 / 전체 {len(labs)}개 → 정책 가족 {fam.family.nunique()}개")

elif args.step == "eval":
    gold = json.load(open(ROOT / "eval" / "gold_families.json", encoding="utf-8"))
    asg = load_assign()
    fam = pd.read_parquet(OUT / "families.parquet") if (OUT / "families.parquet").exists() else None
    topic2fam = dict(zip(fam.topic, fam.family)) if fam is not None else {}
    items = [dict(m, gold=g) for g, ms in gold["families"].items() for m in ms] + \
            [dict(m, gold=None) for m in gold["negatives"]]
    rx = "|".join(f"(?:{m['pattern']})" for m in items)
    hits = []
    for b in pq.ParquetFile(P / "passages.parquet").iter_batches(columns=["pid", "text"], batch_size=300_000):
        s = b.filter(pc.match_substring_regex(b.column("text"), rx)).to_pandas()
        if len(s):
            hits.append(s)
    H = pd.concat(hits).merge(asg[["pid", "council", "topic", "sim"]], on="pid")
    res = []
    for m in items:
        g = H[H.text.str.contains(m["pattern"], regex=True)]
        if m.get("home"):
            g = g[g.council == m["home"]]
        if g.empty:
            res.append({"name": m["name"], "gold": m["gold"], "n": 0})
            continue
        top_topic = int(g.topic.value_counts().index[0])
        res.append({"name": m["name"], "gold": m["gold"], "n": len(g), "topic": top_topic,
                    "topic_share": round(float(g.topic.value_counts(normalize=True).iloc[0]), 3),
                    "family": topic2fam.get(top_topic), "not_in": m.get("not_in")})
    R = pd.DataFrame(res)
    # 쌍 단위 평가: 같은 정답 가족의 두 이름이 같은 예측 단위(가족, 없으면 주제)에 들어갔나
    unit = R.family.where(R.family.notna(), R.topic.map(lambda t: f"t{t}" if pd.notna(t) else None)) if "family" in R else R.topic
    R["unit"] = unit
    pos = R[R.gold.notna() & R.unit.notna()]
    tp = fp = fn = 0
    for i in range(len(pos)):
        for j in range(i + 1, len(pos)):
            same_g = pos.gold.iloc[i] == pos.gold.iloc[j]
            same_p = pos.unit.iloc[i] == pos.unit.iloc[j]
            tp += same_g and same_p; fp += (not same_g) and same_p; fn += same_g and not same_p
    neg = R[R.gold.isna() & R.not_in.notna()]
    fam_unit = {g: pos[pos.gold == g].unit.mode().iloc[0] for g in pos.gold.unique()}
    leaks = [r["name"] for _, r in neg.iterrows() if r.unit is not None and fam_unit.get(r.not_in) == r.unit]
    summ = {"pair_precision": round(tp / max(tp + fp, 1), 3), "pair_recall": round(tp / max(tp + fn, 1), 3),
            "negatives_leaked": leaks, "per_name": R.drop(columns=["unit"]).to_dict(orient="records")}
    json.dump(summ, open(OUT / "eval.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(R.drop(columns=["unit"]).to_string(index=False))
    log(f"쌍 정밀도 {summ['pair_precision']}, 쌍 재현율 {summ['pair_recall']}, 섞여 들어온 음성 대조 {leaks}")
