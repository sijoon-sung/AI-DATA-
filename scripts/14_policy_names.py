"""14단계: 정책 카탈로그 A단계 — 회의록에서 정책 이름 후보를 찾는다(src/catalog/discover.py).

출력
  data/catalog/word_counts.parquet    (말, 의회)별 등장 문단 수와 정책 맥락 문단 수. 새 회의록은 --since로 더한다
  data/catalog/name_candidates.parquet 점수 매긴 후보(전체 등장 수, 의회 수, 집중도, 정책 맥락 비율)
실행: python scripts/14_policy_names.py [--since 2025-01-01] [--until 2024-12-31]
  --until: 그 날짜까지의 회의록만 쓴다(갱신 실험: 2024년으로 만들고 2025년을 나중에 더한다)
"""
import argparse
import sys
import time
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.catalog import discover  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--since", default=None, help="이 날짜 이후 회의록만 세어 기존 집계에 더한다")
ap.add_argument("--until", default=None)
ap.add_argument("--out", default=str(ROOT / "data" / "catalog"))
args = ap.parse_args()
t0 = time.time()
out = Path(args.out)
out.mkdir(parents=True, exist_ok=True)

docs = pd.read_parquet(ROOT / "data" / "processed" / "docs.parquet", columns=["doc_id", "council_short", "date", "keep"])
docs = docs[docs.keep]
if args.since:
    docs = docs[docs.date >= pd.Timestamp(args.since)]
if args.until:
    docs = docs[docs.date <= pd.Timestamp(args.until)]
council_of = dict(zip(docs.doc_id, docs.council_short))
parts = []
for b in pq.ParquetFile(ROOT / "data" / "processed" / "passages.parquet").iter_batches(columns=["doc_id", "n_chars", "text"],
                                                                                       batch_size=200_000):
    keep = pc.and_(pc.is_in(b.column("doc_id"), value_set=pa.array(list(council_of))),
                   pc.greater_equal(b.column("n_chars"), 30))
    b = b.filter(keep)
    if b.num_rows:
        parts.append(discover.count_batch(b.column("doc_id"), b.column("text"), council_of))
counts = discover.merge(parts)
path = out / "word_counts.parquet"
if args.since and path.exists():
    counts = discover.merge([pd.read_parquet(path), counts])
counts.to_parquet(path, index=False)
print(f"[{time.time() - t0:.0f}초] (말, 의회) {len(counts):,}쌍", flush=True)

from kiwipiepy import Kiwi  # noqa: E402
cand = discover.score(counts, Kiwi())
cand.to_parquet(out / "name_candidates.parquet")
print(f"[{time.time() - t0:.0f}초] 후보 {len(cand):,}개", flush=True)
for name, q in {"한 의회 집중(≥0.8)·정책 맥락(≥0.5)": (cand.concentration >= 0.8) & (cand.policy_ctx >= 0.5),
                "여러 의회(≥8)·정책 맥락(≥0.6)": (cand.n_councils >= 8) & (cand.policy_ctx >= 0.6)}.items():
    sub = cand[q]
    print(f"\n{name}: {len(sub):,}개, 상위 40:")
    print(", ".join(f"{w}({r.top_council} {r.total})" for w, r in sub.head(40).iterrows()))
