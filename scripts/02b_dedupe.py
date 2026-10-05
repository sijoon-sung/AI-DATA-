"""2-2단계: 내용이 사실상 같은 회의록(사본) 제거.

HTML이 완전히 같은 중복은 02_preprocess에서 이미 표시했다(dup_of).
여기서는 HTML은 조금 다르지만 본문이 사실상 같은 사본을 찾는다.
같은 의회·같은 회의일자 안에서 두 회의록의 본문을 비교해
  (1) 길이 비율이 0.97 이상이고
  (2) 본문 앞 5,000자와 뒤 2,000자의 유사도가 모두 0.95 이상이면
같은 회의록으로 보고, 본문이 긴 쪽 하나만 남긴다(near_dup_of에 남긴 쪽 id 기록).
최종 분석 대상은 keep == True 인 회의록이다.
"""
import difflib
import re
from pathlib import Path

import pandas as pd

P = Path(__file__).resolve().parents[1] / "data" / "processed"
docs = pd.read_parquet(P / "docs.parquet")
docs["near_dup_of"] = None


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


cand = docs[docs.dup_of.isna()]
bodies = {r.doc_id: norm(r.text[r.body_start:r.body_end]) for r in cand.itertuples()}
n_pairs = 0
for (_, _), g in cand.groupby(["council_short", "date"]):
    if len(g) < 2:
        continue
    ids = sorted(g.doc_id, key=lambda i: -len(bodies[i]))   # 긴 것부터
    kept = []
    for i in ids:
        match = next((k for k in kept if same(bodies[k], bodies[i])), None)
        if match is None:
            kept.append(i)
        else:
            docs.loc[docs.doc_id == i, "near_dup_of"] = match
            n_pairs += 1

docs["keep"] = docs.dup_of.isna() & docs.near_dup_of.isna()
docs.to_parquet(P / "docs.parquet", index=False)
print("본문 사본으로 제외:", n_pairs)
print("최종 분석 대상 회의록:", int(docs.keep.sum()), "/ 원자료", len(docs))
print(docs.groupby(["council_short", "year"]).keep.agg(["size", "sum"]).rename(
    columns={"size": "원자료", "sum": "분석대상"}).to_string())
