"""3단계: 전처리 결과의 품질 점검과 의회별 요약표.

분석 대상은 docs.keep == True 인 회의록(완전 중복과 본문 사본을 뺀 것)이다.
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"
pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 30)

docs = pd.read_parquet(P / "docs.parquet").drop(columns=["text"])
utts = pd.read_parquet(P / "utterances.parquet")
ag = pd.read_parquet(P / "agenda.parquet")

d = docs[docs.keep].copy()
utts = utts[utts.doc_id.isin(d.doc_id)]
d["body_len"] = d.body_end - d.body_start
cov = utts.groupby("doc_id").n_chars.sum()
d["utt_cov"] = (d.doc_id.map(cov).fillna(0) / d.body_len.clip(lower=1)).clip(upper=1)

g = d.groupby(["council_short", "year"])
summ = pd.DataFrame({
    "회의록(원자료)": docs.groupby(["council_short", "year"]).size(),
    "분석대상": g.size(),
    "회의일수": g.date.nunique(),
    "위원회명추출률": g.committee.apply(lambda s: s.notna().mean()).round(2),
    "발언0건": g.n_utt.apply(lambda s: (s == 0).sum()),
    "발언수": g.n_utt.sum(),
    "발언범위비율중앙값": g.utt_cov.median().round(2),
    "본문글자수(백만)": (g.body_len.sum() / 1e6).round(1),
    "발언자형식": g.spk_format.agg(lambda s: s.mode().iat[0]),
}).reset_index()
summ.to_csv(P / "summary_by_council.csv", index=False, encoding="utf-8-sig")
print(summ.to_string())

print("\n[전체] 원자료", len(docs), "/ 분석대상", len(d), "/ 발언", len(utts))
print("본문 총 글자수(백만):", round(d.body_len.sum() / 1e6, 1))
print("의원 측 발언 비율:", round(utts.is_member.mean(), 3))
print("연도별 분석대상:", d.groupby("year").size().to_dict())

ag = ag[ag.doc_id.isin(d.doc_id)].merge(d[["doc_id", "council_short", "year"]], on="doc_id")
uniq = ag.assign(key=ag.title.str.replace(r"\(.*?\)|\s", "", regex=True)) \
    .drop_duplicates(["council_short", "key"])
uniq.to_parquet(P / "agenda_unique.parquet", index=False)
print("\n[의회별 고유 안건 수]")
print(uniq.pivot_table(index="council_short", columns="kind", values="key",
                       aggfunc="count", fill_value=0).to_string())


def mtype(c):
    c = c if isinstance(c, str) else ""
    if "본회의" in c:
        return "본회의"
    if "특별위원회" in c:
        return "특별위원회"
    if "위원회" in c:
        return "상임위원회 등"
    return "미상"


d["회의유형"] = d.committee.map(mtype)
print("\n[회의 유형 구성]")
print(d.groupby(["year", "회의유형"]).size().unstack(fill_value=0).to_string())
print("\n[월별 회의록 수]")
print(d.groupby([d.date.dt.year, d.date.dt.month]).size().unstack(fill_value=0).to_string())
