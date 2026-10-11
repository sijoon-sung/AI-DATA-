"""2단계: 전처리.

원자료(zip 안의 의회별 JSON)를 읽어 다음 세 표를 만든다.
  docs.parquet        회의록 1건 = 1행. 평문 전체(text)와 머리말 정보, 본문 범위를 담는다.
  utterances.parquet  발언 1개 = 1행. 위치(start, end)는 docs.text 기준 문자 위치다.
  agenda.parquet      안건 1개 = 1행.
같은 의회 안에서 HTML이 완전히 같은 회의록은 중복으로 보고 첫 건만 남긴다(dup_of에 원본 id 기록).

메모리를 아끼려고 의회 하나를 처리할 때마다 파일에 이어 쓴다(원문 전체를 한 번에 들고 있지 않는다).
"""
import hashlib
import re
import sys
import time
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.load import DEFAULT_ZIPS, iter_council_files  # noqa: E402
from src.parse import html_to_text  # noqa: E402
from src.segment import parse  # noqa: E402

OUT = ROOT / "data" / "processed"
OUT.mkdir(parents=True, exist_ok=True)

SHORT = {
    "서울특별시의회": "서울", "부산광역시의회": "부산", "대구광역시의회": "대구", "인천광역시의회": "인천",
    "광주광역시의회": "광주", "대전광역시의회": "대전", "울산광역시의회": "울산", "세종특별자치시의회": "세종",
    "경기도의회": "경기", "강원특별자치도의회": "강원", "충청북도의회": "충북", "충청남도의회": "충남",
    "전북특별자치도의회": "전북", "전라남도의회": "전남", "경상북도의회": "경북", "경상남도의회": "경남",
    "제주특별자치도의회": "제주",
}
# 의원 측 발언자로 볼 직함 (집행부·전문위원 등과 구분). 전문위원은 '위원'으로 끝나지만 의원이 아니다.
MEMBER_RE = re.compile(r"^(?:의원|위원|부위원장|(?:[가-힣]*소|임시)?위원장(?:대리|직무대리|직무대행)?"
                       r"|부?의장(?:직무대리|직무대행)?)$")

DOC_SCHEMA = pa.schema([
    ("doc_id", pa.string()), ("year", pa.int64()), ("council", pa.string()), ("council_short", pa.string()),
    ("date", pa.timestamp("us")), ("mtgnm", pa.string()), ("mints_nm", pa.string()), ("committee", pa.string()),
    ("session", pa.float64()), ("session_type", pa.string()), ("sitting", pa.float64()), ("date_line", pa.string()),
    ("spk_format", pa.string()), ("n_utt", pa.int64()), ("n_agenda", pa.int64()), ("body_start", pa.int64()),
    ("body_end", pa.int64()), ("text_len", pa.int64()), ("html_md5", pa.string()), ("dup_of", pa.string()),
    ("text", pa.large_string()),
])
UTT_SCHEMA = pa.schema([
    ("doc_id", pa.string()), ("utt_idx", pa.int64()), ("role", pa.string()), ("name", pa.string()),
    ("is_member", pa.bool_()), ("head_start", pa.int64()), ("start", pa.int64()), ("end", pa.int64()),
    ("n_chars", pa.int64()),
])

doc_w = pq.ParquetWriter(OUT / "docs.parquet", DOC_SCHEMA)
utt_w = pq.ParquetWriter(OUT / "utterances.parquet", UTT_SCHEMA)
agendas, n_docs, n_utts = [], 0, 0
t0 = time.time()
for year, zp in DEFAULT_ZIPS.items():
    for council, recs in iter_council_files(zp):
        if not recs:
            print(f"{year} {council}: 빈 파일, 건너뜀", flush=True)
            continue
        short = SHORT[council]
        seen = {}
        docs, utts = [], []
        # 날짜 순으로 정렬해 id를 매긴다 (같은 날짜는 원래 순서 유지)
        order = sorted(range(len(recs)), key=lambda i: (str(recs[i].get("MTG_DE")), i))
        for k, i in enumerate(order):
            r = recs[i]
            doc_id = f"{year}_{short}_{k:04d}"
            html = r.get("MINTS_HTML") or ""
            h = hashlib.md5(html.encode("utf-8")).hexdigest()
            dup_of = seen.get(h)
            if dup_of is None:
                seen[h] = doc_id
            text = html_to_text(html)
            p = parse(text)
            docs.append(dict(
                doc_id=doc_id, year=year, council=council, council_short=short,
                date=pd.to_datetime(str(r.get("MTG_DE")), format="%Y%m%d", errors="coerce"),
                mtgnm=r.get("MTGNM"), mints_nm=r.get("MINTS_NM"),
                committee=p.header.get("committee"), session=p.header.get("session"),
                session_type=p.header.get("session_type"), sitting=p.header.get("sitting"),
                date_line=p.header.get("date_line"),
                spk_format=p.spk_format, n_utt=len(p.utterances), n_agenda=len(p.agenda),
                body_start=p.body_start, body_end=p.body_end, text_len=len(text),
                html_md5=h, dup_of=dup_of, text=text,
            ))
            if dup_of is not None:
                continue
            for j, u in enumerate(p.utterances):
                utts.append(dict(doc_id=doc_id, utt_idx=j, role=u.role, name=u.name,
                                 is_member=bool(MEMBER_RE.match(u.role)),
                                 head_start=u.head_start, start=u.start, end=u.end,
                                 n_chars=u.end - u.start))
            for a in p.agenda:
                agendas.append(dict(doc_id=doc_id, **a))
        recs = None
        doc_w.write_table(pa.Table.from_pylist(docs, schema=DOC_SCHEMA))
        if utts:
            utt_w.write_table(pa.Table.from_pylist(utts, schema=UTT_SCHEMA))
        n_docs += len(docs)
        n_utts += len(utts)
        docs = utts = None
        print(f"{year} {council}: 누적 회의록 {n_docs:,}, 발언 {n_utts:,}, {time.time() - t0:.0f}초", flush=True)

doc_w.close()
utt_w.close()
agendas = pd.DataFrame(agendas)
agendas.to_parquet(OUT / "agenda.parquet", index=False)
print("docs", n_docs, "utterances", n_utts, "agenda", agendas.shape)
dups = pq.read_table(OUT / "docs.parquet", columns=["dup_of"]).column("dup_of").null_count
print("중복 제외 회의록 수:", dups)
