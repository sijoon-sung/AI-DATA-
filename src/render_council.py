"""의회별 감시 화면: 한 의회가 핵심 이슈를 어디까지 다뤘는지, 다른 의회와 비교해 보여 준다(시민·국회 담당자용).

이슈 카드(JSON)의 의회별 현황을 의회 기준으로 다시 묶은 것이다. 새로 계산하는 값은 비교(몇 번째로 상정했나,
다른 의회는 몇 곳이 했나)뿐이다. 이 화면은 핵심 이슈 40개에 대한 것이며 그 의회의 모든 의정활동이 아니다.
"""
from __future__ import annotations

from src.render_card import STAGE_COLOR, STAGE_ORDER, chip, e

FULL = {"서울": "서울특별시의회", "부산": "부산광역시의회", "대구": "대구광역시의회", "인천": "인천광역시의회",
        "광주": "광주광역시의회", "대전": "대전광역시의회", "울산": "울산광역시의회", "세종": "세종특별자치시의회",
        "경기": "경기도의회", "강원": "강원특별자치도의회", "충북": "충청북도의회", "충남": "충청남도의회",
        "전북": "전북특별자치도의회", "전남": "전라남도의회", "경북": "경상북도의회", "경남": "경상남도의회",
        "제주": "제주특별자치도의회"}
COUNCILS = list(FULL)
ACTED = ("상정", "상임위 가결", "본회의 가결", "기존 조례")

STYLE = """:root{--fg:#2C2C2A;--mut:#5F5E5A;--line:#D3D1C7;--bg:#FAFAF7;--card:#fff;--head:#F1EFE8;--link:#185FA5}
@media (prefers-color-scheme: dark){:root{--fg:#ECEBE6;--mut:#A9A79F;--line:#45443F;--bg:#1C1C1A;--card:#262624;--head:#30302D;--link:#8AB8F0}}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.65 "Pretendard","Apple SD Gothic Neo","Malgun Gothic",sans-serif}
main{max-width:980px;margin:0 auto;padding:28px 16px 60px} h1{font-size:24px;font-weight:600;margin:0 0 4px}
h2{font-size:18px;font-weight:600;margin:32px 0 8px;border-bottom:1px solid var(--line);padding-bottom:6px}
a{color:var(--link)} .note,.sub{font-size:13px;color:var(--mut)}
.chip{display:inline-block;border:1px solid;border-radius:999px;padding:1px 10px;font-size:12.5px;margin:2px 4px 2px 0;white-space:nowrap}
.tw{overflow-x:auto} table{border-collapse:collapse;width:100%;background:var(--card);font-size:14px;min-width:760px}
th,td{border:1px solid var(--line);padding:7px 9px;text-align:left;vertical-align:top} th{background:var(--head);white-space:nowrap}
td.name{min-width:200px} .big{font-size:26px;font-weight:600} .tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:14px 0}
.tile{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 12px}
.nav{display:flex;flex-wrap:wrap;gap:4px;margin:8px 0 0}.nav a{font-size:13px;padding:2px 8px;border:1px solid var(--line);border-radius:999px;text-decoration:none}
.nav a.on{background:var(--head);font-weight:600}"""


def _rows(cards, council):
    out = []
    for c in cards:
        st = {s["council"]: s for s in c["status"]}
        me = st[council]
        bills = sorted([s for s in c["status"] if s.get("bill_date")], key=lambda s: s["bill_date"])
        order = next((i for i, s in enumerate(bills, 1) if s["council"] == council), None)
        conf = [s for s in c["status"] if s.get("confirmed_date")]
        first_conf = min(conf, key=lambda s: s["confirmed_date"])["council"] if conf else None
        fc = next((r for r in (c.get("forecast") or {}).get("councils", []) if r["council_short"] == council), None)
        out.append({"c": c, "me": me, "n_bills_other": sum(1 for s in bills if s["council"] != council),
                    "n_pass_other": sum(1 for s in c["status"] if s["council"] != council and s["stage"] == "본회의 가결"),
                    "order": order, "n_bills": len(bills), "first_bill": bills[0]["council"] if bills else None,
                    "first_conf": first_conf, "fc": fc})
    return out


def bill_name(t: str) -> str:
    """안건 이름에서 발의자 괄호를 뗀다: '…조례안(김○○ 의원 발의)(공동발의자…' → '…조례안'."""
    i = t.find("(")
    j = t.find("발의")
    return t[:i].strip() if i > 0 and j > i else t


def _link(c, prefix):
    return f'<a href="{prefix}{c["issue_id"]}.html">{e(c["title"])}</a>'


def render_council(council: str, cards: list, prefix: str = "../issue_cards/") -> str:
    rows = _rows(cards, council)
    discussed = [r for r in rows if r["me"]["stage"] != "없음"]
    acted = [r for r in rows if r["me"]["stage"] in ACTED]
    passed = [r for r in rows if r["me"]["stage"] == "본회의 가결"]
    led = [r for r in rows if r["first_bill"] == council or r["first_conf"] == council]
    gap = sorted([r for r in rows if r["c"]["kind"] == "inst" and r["me"]["stage"] not in ACTED and r["n_bills_other"] >= 3],
                 key=lambda r: -r["n_bills_other"])
    b = [f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(FULL[council])} 감시 화면</title><style>{STYLE}</style></head><body><main>
<div class="sub">의회별 감시 화면 · 자동 생성(사람 검수 전) · 2024-01~2025-12 회의록 · <a href="../issue_cards/index.html">이슈 목차</a></div>
<h1>{e(FULL[council])}</h1>
<div class="nav">{''.join(f'<a class="{"on" if x == council else ""}" href="{x}.html">{x}</a>' for x in COUNCILS)}</div>
<p class="note">핵심 이슈 {len(cards)}개(여러 의회에 걸친 정책 수단 30개 + 발언에서 자주 나온 정책 이름 10개)에 대해서만 보여 준다. 이 의회의 의정활동 전체가 아니다.
'논의 없음'은 자동 탐지 결과라 표현이 다른 논의를 놓쳤을 수 있다. 판단 근거는 각 이슈 카드의 원문 인용에 있다.</p>
<div class="tiles">
<div class="tile"><div class="note">논의한 이슈</div><div class="big">{len(discussed)}<span class="note"> / {len(cards)}</span></div></div>
<div class="tile"><div class="note">조례 안건으로 나아간 이슈</div><div class="big">{len(acted)}</div></div>
<div class="tile"><div class="note">본회의 가결 확인</div><div class="big">{len(passed)}</div></div>
<div class="tile"><div class="note">17개 의회 중 가장 먼저 다룬 이슈</div><div class="big">{len(led)}</div></div>
</div>"""]

    b.append(f'<h2>다른 의회는 조례를 만들었는데 아직 안건이 없는 이슈 ({len(gap)}개)</h2>'
             '<p class="note">다른 의회 3곳 이상이 조례 안건을 상정한 정책 수단 중, 이 의회에는 안건이 확인되지 않은 것이다. '
             '"법 대응형"은 법이 조례로 정하도록 위임했을 수 있어 이행 여부를 확인할 대상이다. 예측 등급은 다음 6개월 안 상정 가능성이다(2025-12-31 기준).</p>')
    if gap:
        b.append('<div class="tw"><table><tr><th>이슈</th><th>다른 의회 상정(가결)</th><th>이 의회 논의</th><th>이슈 유형</th><th>예측 등급</th></tr>')
        for r in gap:
            me = r["me"]
            talk = f'{me["stage"]} (첫 언급 {me["first_date"]})' if me.get("first_date") else "논의 없음"
            g = f'{r["fc"]["grade"]} ({r["fc"]["p"] * 100:.0f}%)' if r["fc"] else "-"
            t = r["c"]["type"] + (" · 이행 확인 대상" if r["c"]["type"] == "법 대응형" else "")
            b.append(f'<tr><td class="name">{_link(r["c"], prefix)}</td><td>{r["n_bills_other"]}곳 ({r["n_pass_other"]})</td>'
                     f'<td>{e(talk)}</td><td>{e(t)}</td><td>{e(g)}</td></tr>')
        b.append("</table></div>")
    else:
        b.append('<p class="note">해당하는 이슈가 없다.</p>')

    b.append(f'<h2>이 의회가 조례 안건으로 나아간 이슈 ({len(acted)}개)</h2>')
    if acted:
        b.append('<div class="tw"><table><tr><th>이슈</th><th>단계</th><th>안건</th><th>상정 순서</th><th>본회의 가결</th></tr>')
        for r in sorted(acted, key=lambda r: r["me"].get("bill_date", "")):
            me = r["me"]
            od = f'{r["order"]}번째 / {r["n_bills"]}곳' if r["order"] else "-"
            b.append(f'<tr><td class="name">{_link(r["c"], prefix)}</td><td>{chip(me["stage"], STAGE_COLOR[me["stage"]])}</td>'
                     f'<td>{e(me.get("bill_date", ""))} {e(bill_name(me.get("bill_title", "")))}</td><td>{od}</td><td>{e(me.get("plenary_pass", ""))}</td></tr>')
        b.append("</table></div>")

    b.append(f'<h2>17개 의회 중 가장 먼저 다룬 이슈 ({len(led)}개)</h2>'
             '<p class="note">"가장 먼저"는 데이터(2024-01~) 안에서의 관측이다. 그 이전부터 논의된 이슈일 수 있다.</p>')
    for r in led:
        me = r["me"]
        what = []
        if r["first_conf"] == council:
            what.append(f'분명히 다룬 첫 회의 {me.get("confirmed_date")}')
        if r["first_bill"] == council:
            what.append(f'첫 조례 안건 {me.get("bill_date")}')
        b.append(f'<div>{_link(r["c"], prefix)} <span class="note">— {e(", ".join(what))}</span></div>')

    b.append('<h2>핵심 이슈 전체</h2><div class="tw"><table><tr><th>이슈</th><th>단계</th><th>첫 언급</th><th>분명히 다룬 첫 회의</th>'
             '<th>안건</th><th>본회의 가결</th><th>근거 문단</th><th>17곳 중 논의/안건</th></tr>')
    for r in sorted(rows, key=lambda r: (STAGE_ORDER[r["me"]["stage"]], r["c"]["title"])):
        me, c = r["me"], r["c"]
        b.append(f'<tr><td class="name">{_link(c, prefix)}</td><td>{chip(me["stage"], STAGE_COLOR[me["stage"]])}</td>'
                 f'<td>{e(me.get("first_date", ""))}</td><td>{e(me.get("confirmed_date", ""))}</td><td>{e(me.get("bill_date", ""))}</td>'
                 f'<td>{e(me.get("plenary_pass", ""))}</td><td>{me.get("n_passages", 0)}</td><td>{c["n_councils"]} / {r["n_bills"]}</td></tr>')
    b.append("</table></div></main></body></html>")
    return "\n".join(b)
