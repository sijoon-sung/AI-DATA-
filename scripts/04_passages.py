"""4단계: 발언 → 문단 분할 (L1).

출력 passages.parquet: 문단 1개 = 1행.
  pid, doc_id, utt_idx, part, role, name, is_member, start, end, n_chars, text

pid는 '{doc_id}_{start}'다(start = docs.text 기준 문단 시작 위치). 발언 분리 규칙이 바뀌어도
같은 원문 구간이면 같은 ID가 되도록, 발언 번호가 아니라 원문 위치로 만든다(2026-10-11 변경).
메모리를 아끼려고 의회 하나씩 처리해 이어 쓴다.
"""
import sys
import time
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import pandas as pd
import pyarrow as pa
import pyarrow.dataset as ds
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.passages import split_utterance  # noqa: E402

P = ROOT / "data" / "processed"
SCHEMA = pa.schema([
    ("pid", pa.string()), ("doc_id", pa.string()), ("utt_idx", pa.int64()), ("part", pa.int64()),
    ("role", pa.string()), ("name", pa.string()), ("is_member", pa.bool_()), ("start", pa.int64()),
    ("end", pa.int64()), ("n_chars", pa.int64()), ("text", pa.large_string()),
])
t0 = time.time()
meta = pd.read_parquet(P / "docs.parquet", columns=["doc_id", "council_short", "keep"])
meta = meta[meta.keep]
w = pq.ParquetWriter(P / "passages.parquet", SCHEMA)
n, short = 0, 0
for c, cm in meta.groupby("council_short"):
    ids = list(cm.doc_id)
    tbl = ds.dataset(P / "docs.parquet").to_table(columns=["doc_id", "text"], filter=ds.field("doc_id").isin(ids))
    texts = dict(zip(tbl.column("doc_id").to_pylist(), tbl.column("text").to_pylist()))
    tbl = None
    utts = ds.dataset(P / "utterances.parquet").to_table(filter=ds.field("doc_id").isin(ids)).to_pandas()
    rows = {k: [] for k in SCHEMA.names}
    for u in utts.itertuples(index=False):
        t = texts[u.doc_id]
        for k, (s, e) in enumerate(split_utterance(t, u.start, u.end)):
            for key, val in (("pid", f"{u.doc_id}_{s}"), ("doc_id", u.doc_id), ("utt_idx", u.utt_idx), ("part", k),
                             ("role", u.role), ("name", u.name), ("is_member", u.is_member), ("start", s),
                             ("end", e), ("n_chars", e - s), ("text", t[s:e])):
                rows[key].append(val)
    w.write_table(pa.Table.from_pydict(rows, schema=SCHEMA))
    n += len(rows["pid"])
    short += sum(1 for x in rows["n_chars"] if x < 30)
    rows = texts = utts = None
    print(f"{c}: 누적 문단 {n:,}, {time.time() - t0:.0f}초", flush=True)
w.close()
print("문단", n, f"{time.time() - t0:.0f}초")
print("30자 미만 문단 비율:", round(short / max(n, 1), 3))
