"""13단계: 이슈 카드(JSON)로 의회별 감시 화면을 만든다. 모델을 다시 돌리지 않으므로 몇 초면 끝난다.

출력: results/councils/<의회>.html (17개)
실행: python scripts/13_council_views.py   (08_issue_cards.py 다음)
"""
import json
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.render_council import COUNCILS, render_council  # noqa: E402

cards = [json.load(open(f, encoding="utf-8")) for f in sorted((ROOT / "results" / "issue_cards").glob("[IP][0-9]*.json"))]
out = ROOT / "results" / "councils"
out.mkdir(parents=True, exist_ok=True)
for c in COUNCILS:
    (out / f"{c}.html").write_text(render_council(c, cards), encoding="utf-8")
print(f"의회 화면 {len(COUNCILS)}개 → {out} (카드 {len(cards)}장)")
