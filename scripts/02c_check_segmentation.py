"""2-3단계: 발언 분리와 안건 추출의 의회별 회귀 검사.

2026-10-11에 발견한 결함(발언자 경계 누락: 전북 본문의 33.5%, 부산 2025년 안건 누락)이 다시 생기지 않는지 본다.
의회마다 다음을 재고, 다른 의회의 중앙값에서 크게 벗어나면 '확인'으로 표시한다.
  의원 측 발언 비율(발언 수, 글자 수), 교육청 측 글자 비율, 안건 표가 빈 회의록 비율,
  표본 회의록에서 발언자로 잡히지 않은 '○' 줄 비율(머리말 줄 제외).
결과 표는 data/processed/segmentation_check.csv 에도 쓴다.
"""
import re
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import pandas as pd
import pyarrow.dataset as ds

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.segment import parse  # noqa: E402

P = ROOT / "data" / "processed"
docs = pd.read_parquet(P / "docs.parquet", columns=["doc_id", "council_short", "keep", "n_agenda", "date",
                                                    "spk_format", "mints_nm"])
docs = docs[docs.keep]
utts = pd.read_parquet(P / "utterances.parquet", columns=["doc_id", "role", "is_member", "n_chars"])
utts = utts.merge(docs[["doc_id", "council_short"]], on="doc_id")
edu = utts.role.str.contains("교육")

t = pd.DataFrame({
    "의원발언비율": utts.groupby("council_short").is_member.mean(),
    "의원글자비율": utts.assign(m=utts.n_chars * utts.is_member).groupby("council_short").m.sum()
    / utts.groupby("council_short").n_chars.sum(),
    "교육청글자비율": utts.assign(m=utts.n_chars * edu).groupby("council_short").m.sum()
    / utts.groupby("council_short").n_chars.sum(),
    # 행정사무감사 회의록은 원래 안건 목록이 없으므로 뺀다
    "안건빈회의록비율": docs[~docs.mints_nm.str.contains("감사", na=False)]
    .groupby("council_short").n_agenda.apply(lambda s: (s == 0).mean()),
})

# 표본 회의록에서 놓친 '○' 줄 (출석·기록·회의록 머리말 같은 줄은 뺀다)
# 발언자가 아닌 ○ 줄: 출석·기록 머리말, 본문 속 안건 제목(…조례안, …승인안, 5분 자유발언 등)
HEADING = re.compile(r"^○\s*(?:출석|기록|회의록|\d{4}|제\s*\d|[가-힣]*(?:보고서|검토|안건|발언)\b)"
                     r"|조례안|승인안|예산안|동의안|건의안|결의안|계획안|자유발언|보고의?\s*건|\(계속\)")
# 놓친 ○ 줄은 ○로 발언자를 표기하는 A형 회의록에서만 센다(B형: 광주·인천·전남·전북)
sample = docs[docs.spk_format == "A"].sample(frac=1, random_state=0).groupby("council_short").head(20)
tbl = ds.dataset(P / "docs.parquet").to_table(columns=["doc_id", "text"], filter=ds.field("doc_id").isin(list(sample.doc_id)))
miss, tot = {}, {}
for did, text in zip(tbl.column("doc_id").to_pylist(), tbl.column("text").to_pylist()):
    c = did.split("_")[1]
    p = parse(text)
    heads = {u.head_start for u in p.utterances}
    pos = 0
    for line in text.split("\n"):
        s = line.strip()
        lead = len(line) - len(line.lstrip())
        if p.body_start <= pos < p.body_end and s.startswith("○") and not HEADING.match(s):
            tot[c] = tot.get(c, 0) + 1
            if pos + lead not in heads:
                miss[c] = miss.get(c, 0) + 1
        pos += len(line) + 1
t["놓친○줄비율(표본)"] = pd.Series({c: (miss.get(c, 0) / tot[c]) if tot.get(c) else 0.0 for c in t.index})


def flag(row):
    out = []
    med = t.median()
    if abs(row["의원발언비율"] - med["의원발언비율"]) > 0.12:
        out.append("의원발언비율")
    if row["교육청글자비율"] < 0.01:
        out.append("교육청")
    if row["안건빈회의록비율"] > 0.25:
        out.append("안건")
    if row["놓친○줄비율(표본)"] > 0.01:
        out.append("놓친줄")
    return ", ".join(out) if out else "통과"


t["판정"] = t.apply(flag, axis=1)
print(t.round(3).to_string())
print("\n확인이 필요한 의회:", (t["판정"] != "통과").sum(), "/", len(t))
t.round(4).to_csv(P / "segmentation_check.csv", encoding="utf-8-sig")
