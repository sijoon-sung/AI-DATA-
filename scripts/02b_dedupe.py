"""2-2단계: 내용이 사실상 같은 회의록(사본) 제거.

HTML이 완전히 같은 중복은 02_preprocess에서 이미 표시했다(dup_of).
여기서는 HTML은 조금 다르지만 본문이 사실상 같은 사본을 찾는다.
같은 의회·같은 회의일자 안에서 두 회의록의 본문을 비교해
  (1) 길이 비율이 0.97 이상이고
  (2) 본문 앞 5,000자와 뒤 2,000자의 유사도가 모두 0.95 이상이면
같은 회의록으로 보고, 본문이 긴 쪽 하나만 남긴다(near_dup_of에 남긴 쪽 id 기록).
최종 분석 대상은 keep == True 인 회의록이다.

메모리를 아끼려고 의회 하나씩 원문을 읽어 비교하고, 결과 열은 docs.parquet을 흘려 읽으며 덧붙여 쓴다.
"""
import difflib
import os
import re
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import pandas as pd
import pyarrow as pa
import pyarrow.dataset as ds
import pyarrow.parquet as pq

P = Path(__file__).resolve().parents[1] / "data" / "processed"
SRC = P / "docs.parquet"
meta = pd.read_parquet(SRC, columns=["doc_id", "council_short", "year", "date", "dup_of", "body_start", "body_end"])


def norm(s: str) -> str:
    return re.sub(r"\s+", "", s)


def same(a: str, b: str) -> bool:
    la, lb = len(a), len(b)
    if min(la, lb) / max(la, lb, 1) < 0.97:
        return False
    head = difflib.SequenceMatcher(None, a[:5000], b[:5000], autojunk=False).ratio()
    if head < 0.95:
        return False
    tail = difflib.SequenceMatcher(None, a[-2000:], b[-2000:], autojunk=False).ratio()
    return tail >= 0.95


near = {}
cand = meta[meta.dup_of.isna()]
for c, cm in cand.groupby("council_short"):
    multi = cm[cm.duplicated(["date"], keep=False)]
    if multi.empty:
        continue
    tbl = ds.dataset(SRC).to_table(columns=["doc_id", "text"], filter=ds.field("doc_id").isin(list(multi.doc_id)))
    texts = dict(zip(tbl.column("doc_id").to_pylist(), tbl.column("text").to_pylist()))
    bodies = {r.doc_id: norm(texts[r.doc_id][r.body_start:r.body_end]) for r in multi.itertuples()}
    texts = tbl = None
    for _, g in multi.groupby("date"):
        ids = sorted(g.doc_id, key=lambda i: -len(bodies[i]))   # 긴 것부터
        kept = []
        for i in ids:
            match = next((k for k in kept if same(bodies[k], bodies[i])), None)
            if match is None:
                kept.append(i)
            else:
                near[i] = match

# docs.parquet에 near_dup_of, keep 열을 덧붙여 다시 쓴다(흘려 읽기)
tmp = P / "docs.tmp.parquet"
pf = pq.ParquetFile(SRC)
schema = pf.schema_arrow.append(pa.field("near_dup_of", pa.string())).append(pa.field("keep", pa.bool_()))
w = pq.ParquetWriter(tmp, schema)
for b in pf.iter_batches(batch_size=500):
    ids = b.column("doc_id").to_pylist()
    nd = [near.get(i) for i in ids]
    keep = [d is None and n is None for d, n in zip(b.column("dup_of").to_pylist(), nd)]
    w.write_table(pa.Table.from_batches([b]).append_column("near_dup_of", pa.array(nd, pa.string()))
                  .append_column("keep", pa.array(keep, pa.bool_())))
w.close()
pf = None
os.replace(tmp, SRC)

meta["near_dup_of"] = meta.doc_id.map(near)
meta["keep"] = meta.dup_of.isna() & meta.near_dup_of.isna()
print("본문 사본으로 제외:", len(near))
print("최종 분석 대상 회의록:", int(meta.keep.sum()), "/ 원자료", len(meta))
print(meta.groupby(["council_short", "year"]).keep.agg(["size", "sum"]).rename(
    columns={"size": "원자료", "sum": "분석대상"}).to_string())
