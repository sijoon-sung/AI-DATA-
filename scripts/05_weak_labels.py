"""5단계: 문단별 약지도 라벨 생성과 통계.

출력 passages_weak.parquet: pid, council_short, date, n_chars, is_member,
  w_proc, regions(다른 시도 목록, 쉼표 구분), has_generic_other, w_ref, w_topdown
"""
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.weak_labels import (GENERIC_OTHER, find_regions, label_proc, label_ref,  # noqa: E402
                             label_topdown)

P = ROOT / "data" / "processed"
t0 = time.time()
pas = pd.read_parquet(P / "passages.parquet", columns=["pid", "doc_id", "role", "is_member", "n_chars", "text"])
docs = pd.read_parquet(P / "docs.parquet", columns=["doc_id", "council_short", "date", "keep"])
docs = docs[docs.keep]
pas = pas.merge(docs[["doc_id", "council_short", "date"]], on="doc_id")
print("문단", len(pas), f"{time.time() - t0:.0f}초", flush=True)

w_proc, regs, gen, w_ref, w_td = [], [], [], [], []
for r in pas.itertuples(index=False):
    w_proc.append(label_proc(r.role, r.text))
    if r.n_chars >= 30:
        rg = find_regions(r.text, r.council_short)
        regs.append(",".join(sorted({k for k, _, _ in rg})))
        gen.append(bool(GENERIC_OTHER.search(r.text)))
        w_ref.append(label_ref(r.text, rg))
        w_td.append(label_topdown(r.text))
    else:
        regs.append(""); gen.append(False); w_ref.append(None); w_td.append(None)
pas["w_proc"], pas["regions"], pas["has_generic_other"] = w_proc, regs, gen
pas["w_ref"], pas["w_topdown"] = w_ref, w_td
out = pas.drop(columns=["text", "role"])
out.to_parquet(P / "passages_weak.parquet", index=False)
print("완료", f"{time.time() - t0:.0f}초\n")

long_ = pas[pas.n_chars >= 30]
print("[30자 이상 문단]", len(long_))
print("\n(a) 의사진행 약라벨:", pas.w_proc.value_counts(dropna=False).to_dict())
has = long_[long_.regions != ""]
print("\n(c) 다른 시도를 언급한 문단:", len(has), f"({len(has) / len(long_):.1%})",
      "| 그중 의원 측 발언:", int(has.is_member.sum()))
print("    '타 시도·타 지자체·전국 최초' 같은 일반 표현:", int(long_.has_generic_other.sum()))
print("    약라벨:", has.w_ref.value_counts(dropna=False).to_dict())
pr = has[has.w_ref == "POLICY_REF"]
print("    정책 참조 후보(의원 측):", int(pr.is_member.sum()))
print("\n    의회별 '다른 시도 정책 참조' 후보 수 (의원 측 발언):")
print(pr[pr.is_member].groupby("council_short").size().sort_values(ascending=False).to_string())
# 어느 지역이 많이 참조되는가
ex = pr[pr.is_member].assign(r=pr.regions.str.split(",")).explode("r")
print("\n    많이 참조되는 지역:", ex.r.value_counts().head(17).to_dict())
print("\n(d) 하향 요인 단서가 있는 문단:", int((long_.w_topdown == "TOPDOWN").sum()))
