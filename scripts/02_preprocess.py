"""2단계: 전처리.

원자료(zip 안의 의회별 JSON)를 읽어 다음 세 표를 만든다.
  docs.parquet        회의록 1건 = 1행. 평문 전체(text)와 머리말 정보, 본문 범위를 담는다.
  utterances.parquet  발언 1개 = 1행. 위치(start, end)는 docs.text 기준 문자 위치다.
  agenda.parquet      안건 1개 = 1행.
같은 의회 안에서 HTML이 완전히 같은 회의록은 중복으로 보고 첫 건만 남긴다(dup_of에 원본 id 기록).
"""
import hashlib
import sys
import time
from pathlib import Path

import pandas as pd

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
# 의원 측 발언자로 볼 직함 (집행부·전문위원 등과 구분)
MEMBER_ROLES = {"의원", "위원", "위원장", "부위원장", "의장", "부의장", "위원장대리", "위원장직무대리",
                "의장직무대리", "위원장직무대행", "의장직무대행", "부의장직무대리"}

docs, utts, agendas = [], [], []
t0 = time.time()
for year, zp in DEFAULT_ZIPS.items():
    for council, recs in iter_council_files(zp):
        if not recs:
            print(f"{year} {council}: 빈 파일, 건너뜀", flush=True)
            continue
        short = SHORT[council]
        seen = {}
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
                                 is_member=u.role in MEMBER_ROLES,
                                 head_start=u.head_start, start=u.start, end=u.end,
                                 n_chars=u.end - u.start))
            for a in p.agenda:
                agendas.append(dict(doc_id=doc_id, **a))
        print(f"{year} {council}: {len(recs)}건, 누적 발언 {len(utts):,}, {time.time() - t0:.0f}초", flush=True)

docs = pd.DataFrame(docs)
utts = pd.DataFrame(utts)
agendas = pd.DataFrame(agendas)
docs.to_parquet(OUT / "docs.parquet", index=False)
utts.to_parquet(OUT / "utterances.parquet", index=False)
agendas.to_parquet(OUT / "agenda.parquet", index=False)
print("docs", docs.shape, "utterances", utts.shape, "agenda", agendas.shape)
print("중복 제외 회의록 수:", docs["dup_of"].isna().sum())
