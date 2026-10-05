"""1단계: 원자료 목록 조사.

의회·연도별로 회의록 건수, 기간, 회의 종류, HTML 크기, 중복 여부를 집계한다.
HTML 구조를 파악하기 위해 의회별로 자주 쓰인 태그 id/class도 함께 기록한다.
"""
import collections
import json
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.load import DEFAULT_ZIPS, iter_council_files  # noqa: E402

OUT = ROOT / "data" / "processed"
OUT.mkdir(parents=True, exist_ok=True)

rows, mtg_rows, struct = [], [], {}
for year, zp in DEFAULT_ZIPS.items():
    for council, recs in iter_council_files(zp):
        n = len(recs)
        print(year, council, n, flush=True)
        if n == 0:
            rows.append(dict(year=year, council=council, n_records=0))
            continue
        df = pd.DataFrame(recs)
        html_len = df["MINTS_HTML"].fillna("").str.len()
        key = df[["MINTS_NM", "MTG_DE", "MTGNM"]].astype(str).agg("|".join, axis=1)
        rows.append(dict(
            year=year, council=council, n_records=n,
            fields=",".join(sorted(df.columns)),
            nm_values=",".join(sorted(df["RASMBLY_NM"].astype(str).unique())),
            date_min=df["MTG_DE"].min(), date_max=df["MTG_DE"].max(),
            n_dates=df["MTG_DE"].nunique(),
            n_mtgnm=df["MTGNM"].nunique(),
            n_empty_html=int((html_len < 200).sum()),
            html_mb=round(html_len.sum() / 1e6, 1),
            html_len_median=int(html_len.median()),
            n_dup_key=int(key.duplicated().sum()),
            n_dup_html=int(df["MINTS_HTML"].duplicated().sum()),
            n_with_circle=int(df["MINTS_HTML"].fillna("").str.contains("○").sum()),
            out_of_year=int((~df["MTG_DE"].astype(str).str.startswith(str(year))).sum()),
        ))
        for m, c in df["MTGNM"].value_counts().items():
            mtg_rows.append(dict(year=year, council=council, mtgnm=m, n=c))
        # HTML 구조 탐색: 앞 30건에서 id/class 빈도
        ids, classes = collections.Counter(), collections.Counter()
        for h in df["MINTS_HTML"].fillna("").head(30):
            ids.update(re.findall(r'id=["\']([^"\']+)["\']', h))
            classes.update(re.findall(r'class=["\']([^"\']+)["\']', h))
        struct[f"{year}_{council}"] = dict(ids=ids.most_common(25), classes=classes.most_common(25))

inv = pd.DataFrame(rows).sort_values(["council", "year"])
inv.to_csv(OUT / "inventory.csv", index=False, encoding="utf-8-sig")
pd.DataFrame(mtg_rows).to_csv(OUT / "inventory_mtgnm.csv", index=False, encoding="utf-8-sig")
(OUT / "inventory_html_struct.json").write_text(json.dumps(struct, ensure_ascii=False, indent=1), encoding="utf-8")
print(inv.to_string())
