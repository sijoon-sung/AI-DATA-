"""제공 데이터(zip 안의 의회별 JSON)를 읽는 함수 모음.

zip 안의 파일명은 CP949로 저장되어 있으나 zip 헤더에는 UTF-8 플래그가 없다.
그래서 Python zipfile은 이름을 CP437로 해석한다. 이를 다시 CP949로 복원해서 사용한다.
"""
from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Iterator

RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"
DEFAULT_ZIPS = {
    2024: RAW_DIR / "2024_광역 회의록.zip",
    2025: RAW_DIR / "2025_광역 회의록.zip",
}


def member_name(info: zipfile.ZipInfo) -> str:
    """CP437로 잘못 해석된 파일명을 CP949로 복원한다."""
    if info.flag_bits & 0x800:  # UTF-8 플래그가 있으면 그대로 사용
        return info.filename
    return info.filename.encode("cp437").decode("cp949")


def council_from_member(name: str) -> str:
    """'2024_광역 회의록/2024_경기도의회.json' -> '경기도의회'"""
    stem = Path(name).stem              # '2024_경기도의회' 또는 '2025_인천광역시의회 (1)'
    stem = stem.split("_", 1)[1]
    return stem.replace(" (1)", "").strip()


def iter_council_files(zip_path: Path) -> Iterator[tuple[str, list[dict]]]:
    """zip 안의 의회별 JSON을 하나씩 (의회명, 레코드 목록)으로 돌려준다."""
    with zipfile.ZipFile(zip_path) as z:
        for info in z.infolist():
            if info.is_dir() or not info.filename.endswith(".json"):
                continue
            name = member_name(info)
            with z.open(info) as f:
                raw = f.read()
            records = json.loads(raw) if raw.strip() else []
            yield council_from_member(name), records
