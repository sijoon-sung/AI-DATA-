"""4단계: 발언 → 문단 분할 (L1).

출력 passages.parquet: 문단 1개 = 1행.
  pid, doc_id, utt_idx, role, name, is_member, start, end, n_chars, text
"""
import sys
import time
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.passages import split_utterance  # noqa: E402

P = ROOT / "data" / "processed"
t0 = time.time()
docs = pd.read_parquet(P / "docs.parquet", columns=["doc_id", "keep", "text"])
docs = docs[docs.keep]
texts = dict(zip(docs.doc_id, docs.text))
utts = pd.read_parquet(P / "utterances.parquet")
utts = utts[utts.doc_id.isin(texts)]
print("발언", len(utts), f"{time.time() - t0:.0f}초", flush=True)

rows = []
for u in utts.itertuples(index=False):
    t = texts[u.doc_id]
    for k, (s, e) in enumerate(split_utterance(t, u.start, u.end)):
        rows.append((u.doc_id, u.utt_idx, k, u.role, u.name, u.is_member, s, e, e - s, t[s:e]))
pas = pd.DataFrame(rows, columns=["doc_id", "utt_idx", "part", "role", "name", "is_member",
                                  "start", "end", "n_chars", "text"])
pas.insert(0, "pid", pas.doc_id + "_" + pas.utt_idx.astype(str) + "_" + pas.part.astype(str))
pas.to_parquet(P / "passages.parquet", index=False)
print("문단", len(pas), f"{time.time() - t0:.0f}초")
print(pas.n_chars.describe(percentiles=[.1, .25, .5, .75, .9]).round(0).to_string())
print("30자 미만 문단 비율:", round((pas.n_chars < 30).mean(), 3))
