"""9단계: 의회별 검색 색인(BM25 + bge-m3 밀집 벡터). 하이브리드 검색과 RAG 기준선 실험에 쓴다.

본보기:
  - BM25: bm25s (Lù 2024, arXiv:2407.03618, MIT). 토큰은 Kiwi 형태소(명사·어근·용언 어간·외국어·한자)다.
  - 밀집 검색: BGE-M3 (Chen et al. 2024, arXiv:2402.03216, MIT)를 sentence-transformers로 부른다.
  - 둘을 합치는 방법(RRF)은 src/retrieve.py에 있다.

메모리 여유가 적은 PC(16GB, 여유 2~5GB)를 위해 의회 하나씩 만들어 디스크에 둔다.
  data/index/<의회>/meta.parquet   pid, doc_id, date (색인 행 순서)
  data/index/<의회>/dense.npy      (행 수 × 1024) float16, 정규화된 벡터. 검색 때 mmap으로 읽는다
  data/index/<의회>/bm25/          bm25s 색인
대상은 분석 대상 회의록(keep)의 30자 이상 문단이다. 이미 만든 의회는 건너뛰므로 중간에 끊겨도 이어서 만든다.
data/index/는 회의록 원문에서 만든 것이므로 공개 저장소에 올리지 않는다(.gitignore의 data/).

실행: python scripts/09_build_index.py --part bm25     (CPU, 약 50분)
      python scripts/09_build_index.py --part dense    (GPU, 약 2시간)  두 명령은 동시에 돌려도 된다.
"""
import argparse
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
from src.retrieve import COUNCILS, INDEX, bm25_tokens  # noqa: E402

P = ROOT / "data" / "processed"
ap = argparse.ArgumentParser()
ap.add_argument("--part", choices=["bm25", "dense"], required=True)
ap.add_argument("--councils", nargs="*", default=COUNCILS)
ap.add_argument("--batch", type=int, default=128)
args = ap.parse_args()
t0 = time.time()

docs = pd.read_parquet(P / "docs.parquet", columns=["doc_id", "council_short", "date", "keep"])
docs = docs[docs.keep]
pas_ds = ds.dataset(P / "passages.parquet")
model = None
for c in args.councils:
    out = INDEX / c
    done = out / ("bm25" if args.part == "bm25" else "dense.npy")
    if done.exists():
        print(f"{c}: 이미 있음, 건너뜀", flush=True)
        continue
    out.mkdir(parents=True, exist_ok=True)
    ids = docs[docs.council_short == c]
    tbl = pas_ds.to_table(columns=["pid", "doc_id", "n_chars", "text"],
                          filter=(ds.field("doc_id").isin(list(ids.doc_id))) & (ds.field("n_chars") >= 30))
    p = tbl.to_pandas().merge(ids[["doc_id", "date"]], on="doc_id")
    p = p.sort_values(["date", "doc_id", "pid"]).reset_index(drop=True)
    meta = out / "meta.parquet"
    if meta.exists():   # 두 프로세스가 같은 순서를 쓰는지 확인
        old = pd.read_parquet(meta, columns=["pid"])
        if not old.pid.equals(p.pid):
            sys.exit(f"{c}: meta.parquet의 행 순서가 다르다. data/index/{c}/를 지우고 다시 만든다.")
    else:
        p[["pid", "doc_id", "date"]].to_parquet(meta, index=False)
    if args.part == "bm25":
        import bm25s
        toks = bm25_tokens(p.text.tolist())
        r = bm25s.BM25()
        r.index(toks, show_progress=False)
        r.save(str(done))
    else:
        import torch
        from sentence_transformers import SentenceTransformer
        if model is None:
            dev = "cuda" if torch.cuda.is_available() else "cpu"
            model = SentenceTransformer("BAAI/bge-m3", device=dev,
                                        model_kwargs={"torch_dtype": torch.float16 if dev == "cuda" else torch.float32})
            model.max_seq_length = 256
        tmp = out / "dense.tmp.npy"
        mm = np.lib.format.open_memmap(tmp, mode="w+", dtype=np.float16, shape=(len(p), 1024))
        step = 20_000
        for a in range(0, len(p), step):
            mm[a: a + step] = model.encode(p.text.iloc[a: a + step].tolist(), batch_size=args.batch,
                                           normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False)
        mm.flush()
        del mm
        tmp.replace(done)
    print(f"{c}: 문단 {len(p):,}개 {args.part} 완료 ({time.time() - t0:.0f}초)", flush=True)
print(f"전체 완료 ({time.time() - t0:.0f}초)", flush=True)
