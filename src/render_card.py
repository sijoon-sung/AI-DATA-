"""이슈 카드 JSON을 한 장짜리 HTML로 그린다. 차트는 외부 라이브러리 없이 SVG로 그린다(오프라인에서 열림)."""
from __future__ import annotations

import html
import math

COUNCILS = ["서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종", "경기",
            "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주"]
STAGE_ORDER = {"본회의 가결": 0, "상임위 가결": 1, "상정": 2, "기존 조례": 3, "실질 논의": 4, "언급": 5, "없음": 6}
STAGE_COLOR = {"본회의 가결": "#0F6E56", "상임위 가결": "#1D9E75", "상정": "#BA7517", "기존 조례": "#534AB7",
               "실질 논의": "#378ADD", "언급": "#85B7EB", "없음": "#B4B2A9"}

e = html.escape


def chip(text, color):
    return f'<span class="chip" style="background:{color}1f;color:{color};border-color:{color}66">{e(text)}</span>'


def cite_html(c, show_doc=True):
    if not c:
        return ""
    v = "" if c.get("verified") in (None, True) else ' <span class="warn">원문 불일치</span>'
    doc = f' · {e(c["doc"])}' if show_doc and c.get("doc") else ""
    role = f' · {e(str(c["role"]))}' if c.get("role") else ""
    kind = " · 안건 제목(안건 표에서)" if c.get("kind") == "안건 제목" else ""
    if c.get("via") == "semantic":
        kind += " · 별칭 없이 의미 검색으로 찾음"
    return (f'<div class="cite"><div class="q">"{e(c["quote"])}"</div>'
            f'<div class="src">{e(c["council"])} · {e(c["date"])}{doc}{role}{kind}{v}</div></div>')


def yoy(tr):
    h = tr["halves"]
    a, z = (h["2024H1"] + h["2024H2"]) / 2, (h["2025H1"] + h["2025H2"]) / 2
    return (z - a) / a * 100 if a else 0.0


# ---------------------------------------------------------------- 차트
def national_bars(tr):
    nat = tr["national"]
    W, H, L, B = 660, 190, 40, 30
    bw = (W - L - 10) / len(nat)
    mx = max(x["per10k"] for x in nat) or 1
    s = [f'<svg viewBox="0 0 {W} {H}" class="chart" role="img"><title>월별 논의량</title>']
    for t in (0, mx / 2, mx):
        y = H - B - (H - B - 20) * t / mx
        s.append(f'<line x1="{L}" y1="{y:.1f}" x2="{W - 10}" y2="{y:.1f}" class="grid"/>'
                 f'<text x="{L - 6}" y="{y + 4:.1f}" class="ax" text-anchor="end">{t:.1f}</text>')
    for i, x in enumerate(nat):
        h = (H - B - 20) * x["per10k"] / mx
        X = L + i * bw + 2
        s.append(f'<rect x="{X:.1f}" y="{H - B - h:.1f}" width="{bw - 4:.1f}" height="{h:.1f}" class="bar">'
                 f'<title>{x["month"]}: 1만 문단당 {x["per10k"]} ({x["hits"]}문단)</title></rect>')
        if x["month"].endswith(("-01", "-07")):
            s.append(f'<text x="{X + bw / 2:.1f}" y="{H - 10}" class="ax" text-anchor="middle">{x["month"][2:]}</text>')
    s.append("</svg>")
    return "".join(s)


def dot_matrix(card):
    tr = card["trend"]
    months, grid = tr["months"], tr["grid"]
    st = {s["council"]: s for s in card["status"]}
    order = sorted(COUNCILS, key=lambda c: st[c].get("first_date", "9999"))
    W, L, T, cw, rh = 680, 46, 26, 26, 22
    H = T + rh * len(order) + 30
    mx = max(max(v) for v in grid.values()) or 1
    s = [f'<svg viewBox="0 0 {W} {H}" class="chart" role="img"><title>의회별 월별 논의와 조례 단계</title>']
    for j, m in enumerate(months):
        if m.endswith(("-01", "-04", "-07", "-10")):
            s.append(f'<text x="{L + j * cw + cw / 2}" y="{T - 10}" class="ax" text-anchor="middle">{m[2:]}</text>')
    for i, c in enumerate(order):
        y = T + i * rh + rh / 2
        s.append(f'<text x="{L - 8}" y="{y + 4}" class="lab" text-anchor="end">{c}</text>'
                 f'<line x1="{L}" y1="{y}" x2="{L + cw * len(months)}" y2="{y}" class="grid"/>')
        for j, v in enumerate(grid[c]):
            if v > 0:
                r = 2 + 8 * math.sqrt(v / mx)
                s.append(f'<circle cx="{L + j * cw + cw / 2}" cy="{y}" r="{r:.1f}" class="dot">'
                         f'<title>{c} {months[j]}: 1만 문단당 {v}</title></circle>')

        def mark(date, shape):
            if not date:
                return
            mm = date[:7]
            if mm in months:
                x = L + months.index(mm) * cw + cw / 2
                if shape == "sq":
                    s.append(f'<rect x="{x - 5}" y="{y - 5}" width="10" height="10" class="m-bill"><title>{c} 조례 상정 {date}</title></rect>')
                else:
                    s.append(f'<path d="M{x} {y - 7} L{x + 6} {y} L{x} {y + 7} L{x - 6} {y} Z" class="m-pass"><title>{c} 본회의 가결 {date}</title></path>')
        mark(st[c].get("bill_date"), "sq")
        mark(st[c].get("plenary_pass"), "dia")
    s.append(f'<g transform="translate({L},{H - 12})"><circle cx="6" cy="-4" r="5" class="dot"/>'
             f'<text x="16" y="0" class="ax">논의량(원 크기)</text>'
             f'<rect x="120" y="-9" width="10" height="10" class="m-bill"/><text x="136" y="0" class="ax">조례 상정</text>'
             f'<path d="M226 -11 L232 -4 L226 3 L220 -4 Z" class="m-pass"/><text x="238" y="0" class="ax">본회의 가결</text></g>')
    s.append("</svg>")
    return "".join(s)


# ---------------------------------------------------------------- 문장 (템플릿)
def summary_rows(card):
    st = card["status"]
    bills = [s for s in st if s.get("bill_date")]
    passed = [s for s in st if s["stage"] == "본회의 가결"]
    exist = [s for s in st if s["stage"] == "기존 조례"]
    first, fconf = card["first"], card.get("first_confirmed")
    kw = ", ".join(dict.fromkeys(w for c in card["clusters"]["clusters"][:4] for w in c["keywords"][:2])) if card.get("clusters") else ""
    rows = []
    rep_bill = min(bills, key=lambda s: s["bill_date"]) if bills else None
    rows.append(("주요 이슈 키워드", f'{card["title"]}' + (f' (주제: {card["theme"]})' if card.get("theme") else "")
                 + (f' — 대표 안건 「{rep_bill["bill_title"]}」' if rep_bill else "") + (f' · 주요 쟁점어: {kw}' if kw else "")))
    lead = (f'데이터 시작(2024-01) 뒤 3개월 안에 {card["n_early"]}개 의회가 이미 언급해, 기원은 데이터 이전일 수 있다(좌측 절단). '
            if card["left_censored"] else "")
    if fconf:
        t = lead + f'데이터 안 최초 관측(관련성 확인): {fconf["council"]}, {fconf["confirmed_date"]} ({fconf["confirmed"]["doc"]}).'
        if first and first["first_date"] < fconf["confirmed_date"]:
            t += f' 그보다 이른 {first["council"]} {first["first_date"]}의 언급은 관련 점수가 낮아 최초로 보지 않는다.'
    elif first:
        t = lead + f'데이터 안 최초 관측: {first["council"]}, {first["first_date"]} ({first["first"]["doc"]}). 관련성은 확인되지 않았다.'
    else:
        t = "관측 없음."
    if rep_bill:
        t += f' 조례 기준 첫 안건: {rep_bill["council"]} {rep_bill["bill_date"]}.'
    rows.append(("등장 시점", t))
    order = " → ".join(f'{s["council"]}({s["bill_date"][:7]})' for s in sorted(bills, key=lambda s: s["bill_date"]))
    flow = (f'논의 {card["n_councils"]}/17곳, 조례·안건 {len(bills)}곳(본회의 가결 확인 {len(passed)}곳, '
            f'기존 조례 {len(exist)}곳). ' + (f'상정 순서: {order}. ' if order else "")
            + f'유형: {card["type"]} — {card["type_why"]}.')
    rows.append(("타 지방의회로의 흐름", flow))
    fc = card.get("forecast")
    if fc and fc["councils"]:
        g = {}
        for r in fc["councils"]:
            g.setdefault(r["grade"], []).append(r["council_short"])
        gtxt = ", ".join(f'{k} {len(v)}곳({"·".join(v)})' for k, v in g.items())
        t = (f'기준 {fc["origin"]}. 확산 단계: {fc["stage"]}(안건 {fc["n_any"]}곳, 최근 6개월 신규 {int(fc["recent6"])}곳). '
             f'다음 6개월 신규 상정 예상 {fc["expected_new"]}곳(80% 구간 {fc["interval80"][0]}~{fc["interval80"][1]}곳). 의회별 등급: {gtxt}.')
    elif fc:
        t = (f'기준 {fc["origin"]}. 확산 단계: 포화 — 17개 의회 모두 이미 안건을 냈다(최근 6개월 신규 {int(fc["recent6"])}곳). '
             '새로 상정할 의회가 남지 않아 신규 확산 예측은 0곳이다. 이후 관심은 개정·후속 사업으로 옮겨 간다.')
    else:
        t = f'조례 확산 예측 없음: {card.get("forecast_note") or "예측 모형의 대상이 아니다"}. ' + outlook_text(card)
    up = card["upward"]
    if up["bills"]:
        t += " 상향 신호: " + "; ".join(f'{b["council"]} 「{b["title"]}」({b["date"]})' for b in up["bills"]) + "."
    rows.append(("향후 예측", t))
    n_cite = 1 + len(card["ref_examples"]) + len(card.get("reasons", []))
    rows.append(("근거 회의록", f"아래 각 절의 인용 {n_cite}건 이상(회의록명·일자·원문 구간, 원문 일치 검사)."))
    return rows


def outlook_text(card):
    o = card.get("outlook")
    if not o:
        return ""
    ch = f'{o["change"]:+.0f}%' if o.get("change") is not None else "계산 불가"
    return (f'논의 지표로 본 전망(모형 아님): {o["stage"]} — 관련성 확인 의회 {o["n_confirmed"]}곳, '
            f'2025 하반기에 새로 논의를 시작한 의회 {o["new_2025h2"]}곳, 2025 하반기 논의량 {ch}(상반기 대비).')


def within_auc_text(fc):
    ms = [m for m in (fc or {}).get("metrics", []) if m.get("within_auc") is not None]
    if not ms:
        return "같은 이슈 안에서 의회 순위를 가리는 힘은 따로 재지 못했다."
    return ("같은 이슈 안에서 어느 의회가 먼저 할지 가리는 힘은 약하다(이슈 내 AUC "
            + ", ".join(f'{m["origin"][:7]} {m["within_auc"]}' for m in ms) + "). 등급은 이슈 단위로 읽는 것이 맞다.")


# ---------------------------------------------------------------- 페이지
def render(card):
    st = sorted(card["status"], key=lambda s: (STAGE_ORDER[s["stage"]], s.get("bill_date") or s.get("first_date") or "9"))
    stage_counts = {k: sum(1 for s in st if s["stage"] == k) for k in STAGE_ORDER}
    tr = card["trend"]
    fc = card.get("forecast")
    b = []
    b.append(f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(card['title'])} 이슈 카드</title><style>
:root{{--fg:#2C2C2A;--mut:#5F5E5A;--line:#D3D1C7;--bg:#FAFAF7;--card:#fff;--acc:#0F6E56}}
body{{margin:0;background:var(--bg);color:var(--fg);font:15px/1.65 "Pretendard","Apple SD Gothic Neo","Malgun Gothic",sans-serif}}
main{{max-width:900px;margin:0 auto;padding:28px 18px 60px}}
h1{{font-size:24px;margin:0 0 6px;font-weight:600}} h2{{font-size:18px;margin:34px 0 10px;font-weight:600;border-bottom:1px solid var(--line);padding-bottom:6px}}
.sub{{color:var(--mut);font-size:13px}} .chip{{display:inline-block;border:1px solid;border-radius:999px;padding:1px 10px;font-size:12.5px;margin:2px 4px 2px 0;white-space:nowrap}}
.tw{{overflow-x:auto}} .tw table{{min-width:720px}}
table{{border-collapse:collapse;width:100%;background:var(--card);font-size:14px}} th,td{{border:1px solid var(--line);padding:7px 9px;vertical-align:top;text-align:left}}
th{{background:#F1EFE8;font-weight:600;white-space:nowrap}} .row-k{{width:150px;background:#F1EFE8;font-weight:600}}
.cite{{border-left:3px solid var(--line);padding:4px 10px;margin:6px 0;background:var(--card)}} .q{{font-size:14px}} .src{{color:var(--mut);font-size:12.5px}}
.warn{{color:#A32D2D;font-weight:600}} .box{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 14px;margin:10px 0}}
.grid2{{display:grid;grid-template-columns:1fr 1fr;gap:12px}} @media(max-width:700px){{.grid2{{grid-template-columns:1fr}}}}
.chart{{width:100%;height:auto;background:var(--card);border:1px solid var(--line);border-radius:10px}}
.chart .grid{{stroke:#E5E3DA;stroke-width:1}} .chart .ax{{font-size:11px;fill:#5F5E5A}} .chart .lab{{font-size:12px;fill:#2C2C2A}}
.chart .bar{{fill:#5DCAA5}} .chart .dot{{fill:#378ADD;fill-opacity:.55}} .chart .m-bill{{fill:#EF9F27;stroke:#854F0B;stroke-width:1}} .chart .m-pass{{fill:#0F6E56}}
.kw{{font-weight:600}} .note{{font-size:13px;color:var(--mut)}} .big{{font-size:26px;font-weight:600;color:var(--acc)}}
</style></head><body><main>""")
    b.append(f"""<div class="sub">이슈 카드 · 자동 생성(사람 검수 전) · 2024-01~2025-12 17개 광역의회 회의록 · LLM 미사용</div>
<h1>{e(card['title'])}</h1><div class="sub">주제: {e(card.get('theme') or '-')} · {'안건 제목에서 도출한 정책 수단' if card.get('kind') == 'inst' else '발언에서만 나오는 정책 고유명사'} · 검색 별칭: {e(', '.join(card.get('aliases', [])[:6]))}</div>
<div>{chip(card['type'], '#534AB7')}"""
             + (chip('확산 단계: ' + fc['stage'], '#BA7517') if fc else chip('논의 전망: ' + card['outlook']['stage'], '#888780') if card.get('outlook') else '')
             + chip(f"논의량: 2025 하반기 {tr['change_25h2_vs_25h1']:+.0f}%(상반기 대비), 2025년 {yoy(tr):+.0f}%(2024년 대비)", '#185FA5')
             + chip(f"논의 {card['n_councils']}/17곳 · 근거 문단 {card['n_passages']:,}개(후보 {card.get('n_candidates', card['n_passages']):,}개)", '#5F5E5A') + "</div>")
    b.append('<h2>대회 결과표 형식</h2><table>')
    for k, v in summary_rows(card):
        b.append(f'<tr><td class="row-k">{e(k)}</td><td>{e(v)}</td></tr>')
    b.append("</table>")
    b.append("<h2>1. 17개 의회 현황</h2><div>" + "".join(chip(f"{k} {v}", STAGE_COLOR[k]) for k, v in stage_counts.items() if v) + "</div>")
    b.append("<div class=\"tw\"><table><tr><th>의회</th><th>단계</th><th>첫 언급</th><th>확인된 첫 관측</th><th>실질 논의</th><th>조례·안건</th><th>가결</th><th>비고</th></tr>")
    for s in st:
        note = []
        if s.get("existing_claim"):
            note.append("이미 만들었다는 발언 있음(확인 필요)")
        if s.get("pass_how") in ("일괄 처리", "직전 문맥"):
            note.append(f"가결 판정: {s['pass_how']}(근사)")
        if s.get("held"):
            note.append(s["held"])
        bill = f'{s.get("bill_date", "")} {e(s.get("bill_title", ""))}' if s.get("bill_date") else ""
        pas = s.get("plenary_pass") or (("상임위 " + s["committee_pass"]) if s.get("committee_pass") else "")
        b.append(f'<tr><td>{s["council"]}</td><td>{chip(s["stage"], STAGE_COLOR[s["stage"]])}</td><td>{s.get("first_date", "")}</td>'
                 f'<td>{s.get("confirmed_date", "")}</td>'
                 f'<td>{s.get("sub_date", "")}</td><td>{bill}</td><td>{pas}</td><td class="note">{e("; ".join(note))}</td></tr>')
    b.append("</table></div>")
    b.append(f"""<h2>2. 트렌드</h2><p>전국 회의록 1만 문단당 언급 문단 수(회의량으로 나눈 값). 정점 <b>{tr['peak']}</b>.
반기별: 2024 상 {tr['halves']['2024H1']} → 2024 하 {tr['halves']['2024H2']} → 2025 상 {tr['halves']['2025H1']} → 2025 하 {tr['halves']['2025H2']}.
논의한 의회 수(분기): {' · '.join(f"{q['q']} {q['councils']}" for q in tr['councils_by_quarter'])}.</p>{national_bars(tr)}""")
    b.append(f"""<h2>3. 흐름</h2><p>의회별로 언제 얼마나 논의했는지(원), 언제 조례를 상정하고 가결했는지(표식). 위에서 아래로 첫 언급 순서다.
<b>첫 언급 순서는 회기 일정의 영향을 크게 받으므로 확산 경로로 읽지 않는다.</b> 화살표(의회 간 연결)는 아래의 명시적 참조나 공통 법령 근거가 있을 때만 말한다.</p>{dot_matrix(card)}""")
    b.append(f'<div class="box"><b>유형: {e(card["type"])}</b><br>{e(card["type_why"])}</div>')
    if card["ref_examples"]:
        b.append(f'<h3>● 명시적 참조 후보 ({len(card["edges"])}개 의회 쌍, 자동 탐지)</h3>')
        for r in card["ref_examples"][:8]:
            b.append(f'<div class="note">{e(r["council"])} → {e(r["to"])} 사례 언급</div>' + cite_html(r))
    if card.get("top_law"):
        tl = card["top_law"]
        b.append(f'<h3>■ 법령 인용</h3><p>가장 많이 인용된 특정 법령: 「{e(tl["law"])}」 — {int(tl["councils"])}개 의회, {int(tl["n"])}건, 시행·위임 표현 {int(tl["trig"])}건.</p>'
                 + cite_html(tl.get("example")))
    cl = card.get("clusters")
    if cl:
        b.append(f'<h2>4. 쟁점 (발언 문장 {cl["n_sentences"]:,}개를 bge-m3로 {cl["k"]}개 묶음으로 군집)</h2>'
                 '<p class="note">각 묶음의 단어는 그 묶음에서 두드러진 명사(자동), 인용은 묶음 중심에 가까운 문장을 의회별로 하나씩 뽑은 것이다. 요약문을 새로 쓰지 않고 원문만 보여 준다.</p>')
        for i, c in enumerate(cl["clusters"], 1):
            b.append(f'<div class="box"><span class="kw">쟁점 {i}: {e(" · ".join(c["keywords"]))}</span> '
                     f'<span class="note">— {c["n_councils"]}개 의회, 문장 {c["n_sent"]}개, 의원 발언 {int(c["member_share"] * 100)}%</span>')
            for r in c["reps"]:
                b.append(cite_html(r))
            b.append("</div>")
    if card.get("reasons"):
        b.append('<h2>5. 의회들이 말한 도입 이유</h2><p class="note">조례 제안설명 등에서 "~하기 위하여" 문장을 발언자에게 귀속해 옮긴 것이다. 시스템이 원인을 판단한 것이 아니다.</p>')
        for r in card["reasons"][:8]:
            b.append(cite_html(r))
    b.append("<h2>6. 향후 예측 (기준 2025-12-31)</h2>")
    if fc and not fc["councils"]:
        b.append(f'<div class="box"><b>포화</b> — 17개 의회 모두 이미 안건을 냈다(최근 6개월 신규 {int(fc["recent6"])}곳). '
                 '새로 상정할 의회가 남지 않아 신규 확산 예측 대상이 없다.</div>')
    elif fc:
        b.append(f"""<div class="grid2"><div class="box"><div class="note">다음 6개월 신규 조례 상정 예상</div><div class="big">{fc['expected_new']}곳</div>
<div class="note">80% 구간 {fc['interval80'][0]}~{fc['interval80'][1]}곳 · 아직 안 한 의회 {len(fc['councils'])}곳의 예측 확률 합</div></div>
<div class="box"><div class="note">확산 단계</div><div class="big">{e(fc['stage'])}</div><div class="note">안건 {fc['n_any']}곳 · 최근 6개월 신규 {int(fc['recent6'])}곳</div></div></div>
<table><tr><th>의회</th><th>등급</th><th>예측 확률</th><th>비고</th></tr>""")
        for r in fc["councils"]:
            b.append(f'<tr><td>{r["council_short"]}</td><td>{r["grade"]}</td><td>{r["p"] * 100:.1f}%</td><td class="note">{e(r.get("flag", ""))}</td></tr>')
        gm = "; ".join(f"{k} {v['rate'] * 100:.1f}% [{v['ci'][0] * 100:.1f}~{v['ci'][1] * 100:.1f}] (n={v['n']:,})"
                       for k, v in fc["grades"].items() if v.get("rate") is not None)
        b.append(f"""</table><p class="note">기저율 {fc['b0'] * 100:.2f}%. 등급의 뜻(2025-01·2025-07 기준점 백테스트에서 실제로 맞은 비율, 95% 신뢰구간): {gm}.
모형은 안건 표만으로 만든 간이 로지스틱이며, 상위 확률은 과신하는 경향이 있어 등급과 실측 빈도로 읽는다. {within_auc_text(fc)}</p>""")
    else:
        b.append(f'<div class="box">조례 확산 예측 없음: {e(card.get("forecast_note") or "예측 모형의 대상이 아니다")}.<br>{e(outlook_text(card))}</div>')
    up = card["upward"]
    b.append(f'<h3>상향 신호 (국회 입법 요구)</h3><p>건의·결의안 {len(up["bills"])}건, "법 제정·개정 촉구/필요" 같은 발언 {up["talk_n"]}건({up["talk_councils"]}개 의회).</p>')
    for x in up["bills"]:
        b.append(f'<div class="cite"><div class="q">「{e(x["title"])}」</div><div class="src">{e(x["council"])} · {e(x["date"])} · 안건({e(x["act"])})</div></div>')
    if up.get("talk_example"):
        b.append(cite_html(up["talk_example"]))
    first = card["first"]
    fconf = card.get("first_confirmed")
    b.append("<h2>7. 근거와 한계</h2>" + "<h3>최초 관측 근거</h3>"
             + (cite_html(fconf["confirmed"]) if fconf else "")
             + (cite_html(first["first"]) if first and not (fconf and first["first"] == fconf["confirmed"]) else ""))
    allc = ([fconf["confirmed"]] if fconf else []) + ([first["first"]] if first and not (fconf and first["first"] == fconf["confirmed"]) else [])         + card["ref_examples"] + card.get("reasons", [])
    allc = [c for c in allc if c.get("verified") is not None]   # 안건 제목 인용은 안건 표에서 온 것이라 문단 대조 대상이 아니다
    ver = sum(1 for c in allc if c.get("verified"))
    if card.get("alias_stats"):
        b.append('<h3>검색 별칭과 관련 비율</h3><p class="note">별칭마다 걸린 후보 문단 수와, 그중 관련 점수(bge-reranker) 0.5 이상인 비율. '
                 '관련 비율이 대표 별칭의 절반에 못 미치는 별칭은 이름만 같은 다른 이야기를 많이 끌어오는 넓은 별칭으로 보고, '
                 '그 별칭으로만 걸린 문단은 관련 점수 0.5 이상일 때만 쓴다. 관련 점수는 짧은 대화체 언급에도 낮게 나오므로 핵심 별칭의 문단은 점수로 거르지 않는다.</p>'
                 '<table><tr><th>별칭</th><th>후보 문단</th><th>관련 비율</th><th>쓰는 방법</th></tr>')
        for a in card["alias_stats"]:
            prec = "" if a.get("prec") is None else f'{a["prec"] * 100:.0f}%'
            b.append(f'<tr><td>{e(a["alias"])}</td><td>{a["n"]:,}</td><td>{prec}</td><td class="note">{e(a.get("status", ""))}</td></tr>')
        b.append("</table>")
    b.append(f"""<div class="box note">원문 일치 검사: 발언 인용 {len(allc)}건 중 {ver}건이 원문 문단과 글자까지 일치.<br>
자동 생성 결과이며 사람이 검수하지 않았다. 후보 문단은 별칭 정규식으로 넓게 찾고, 이 이슈를 분명히 다루는지는 교차 인코더(bge-reranker-v2-m3)의 관련 점수로 판정했다(확인된 최초 관측, 넓은 별칭의 문단).
다른 의회 사례 언급은 규칙으로 찾은 뒤 한국어 NLI 판정기(KoELECTRA, KLUE-NLI 학습)로 걸렀다. 쟁점은 bge-m3 군집이다. LLM은 쓰지 않았다.<br>
한계: 관련 점수 경계(0.5)와 별칭 구분 규칙은 아직 사람 정답으로 검증하지 않았다. 가결 여부는 회의록 본문의 선포 문장을 규칙으로 찾은 근사다.
제안설명의 절반 이상이 유인물로 대체되어 법령명·제안 이유가 회의록에 남지 않는 경우가 많다.</div>""")
    b.append("</main></body></html>")
    return "\n".join(b)


# ---------------------------------------------------------------- 대회 결과표와 목차
def competition_row(card):
    """대회 요구 항목(주요 이슈 키워드, 최초 관측 시점, 다른 의회로의 흐름, 향후 확산 가능성, 근거)을 한 행으로."""
    rows = dict(summary_rows(card))
    cites = []
    fconf, first = card.get("first_confirmed"), card.get("first")
    if fconf:
        cites.append(fconf["confirmed"])
    elif first:
        cites.append(first["first"])
    cites += card.get("ref_examples", [])[:2] + card.get("reasons", [])[:1]
    ev = " | ".join(f'[{c["council"]}] {c["doc"]} ({c["date"]}): "{c["quote"]}"' for c in cites if c)
    return {"이슈키워드": rows["주요 이슈 키워드"], "등장시점": rows["등장 시점"], "타 지방의회로의 흐름": rows["타 지방의회로의 흐름"],
            "향후 예측": rows["향후 예측"], "근거 회의록": ev, "이슈 유형": card["type"], "주제": card.get("theme", ""),
            "이슈 ID": card["issue_id"]}


def stage_cell(c):
    fc, o = c.get("forecast"), c.get("outlook")
    if fc:
        return e(fc["stage"])
    return f'<span class="note">논의: {e(o["stage"])}</span>' if o else "-"


def render_index(cards, fc_meta):
    def table(group):
        rows = []
        for i, c in enumerate(group, 1):
            st = c["status"]
            n_bill = sum(1 for s in st if s.get("bill_date"))
            n_pass = sum(1 for s in st if s["stage"] == "본회의 가결")
            fc = c.get("forecast")
            up = "있음" if c["upward"]["bills"] else ""
            rows.append(f'<tr><td>{i}</td><td class="name"><a href="{c["issue_id"]}.html">{e(c["title"])}</a><div class="note">{e(c.get("theme") or "")}</div></td>'
                        f'<td>{chip(c["type"], "#534AB7")}</td><td>{c["n_councils"]}</td><td>{n_bill} ({n_pass})</td>'
                        f'<td>{stage_cell(c)}</td><td>{fc["expected_new"] if fc else "-"}</td>'
                        f'<td>{c["trend"]["yoy"]:+.0f}%</td><td>{up}</td></tr>')
        return ('<div class="tw"><table><tr><th>#</th><th>이슈</th><th>유형</th><th>논의 의회</th><th>조례(가결)</th><th>확산 단계</th>'
                '<th>6개월 신규 예상</th><th>논의량 2025/2024</th><th>상향 신호</th></tr>' + "".join(rows) + "</table></div>")
    inst = [c for c in cards if c.get("kind") == "inst"]
    prop = sorted([c for c in cards if c.get("kind") != "inst"], key=lambda c: (-c["n_councils"], -c["n_passages"]))
    metrics = "; ".join(f'기준점 {m["origin"]}: AUC {m["auc"]}(이슈 안 {m.get("within_auc", "-")}), Brier 기술 점수 {m["brier_skill"]:+.3f}, '
                        f'사건 {m["events"]}/{m["pairs"]:,}' for m in fc_meta.get("metrics", []))
    return f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>광역의회 정책 이슈 확산 목차</title><style>
:root{{--fg:#2C2C2A;--bg:#FAFAF7;--card:#fff;--line:#D3D1C7;--head:#F1EFE8;--mut:#5F5E5A;--link:#185FA5}}
body{{margin:0;background:var(--bg);color:var(--fg);font:15px/1.6 "Pretendard","Apple SD Gothic Neo","Malgun Gothic",sans-serif}}
main{{max-width:1040px;margin:0 auto;padding:28px 16px 60px}} h1{{font-size:24px;font-weight:600;margin:0 0 6px}} h2{{font-size:18px;font-weight:600;margin:30px 0 8px}}
table{{border-collapse:collapse;width:100%;background:var(--card);font-size:14px}} th,td{{border:1px solid var(--line);padding:7px 9px;text-align:left;vertical-align:top}}
th{{background:var(--head);white-space:nowrap}} a{{color:var(--link)}} .note{{font-size:12.5px;color:var(--mut)}} .tw{{overflow-x:auto}} .tw table{{min-width:900px}}
td.name{{min-width:220px}}
.chip{{display:inline-block;border:1px solid;border-radius:999px;padding:1px 10px;font-size:12.5px;white-space:nowrap}}
</style></head><body><main><div class="note">자동 생성 · 사람 검수 전 · 2024-01~2025-12 17개 광역의회 회의록 · LLM 미사용(규칙 + 인코더)</div>
<h1>광역의회 정책 이슈 확산 목차</h1>
<p class="note">의회별 감시 화면: {" · ".join(f'<a href="../councils/{x}.html">{x}</a>' for x in ["서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종", "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주"])}</p>
<p class="note">핵심 이슈 {len(cards)}개. 조례 수 괄호 안은 본회의 가결이 확인된 의회 수. 예측 백테스트 — {e(metrics)}</p>
<h2>조례로 퍼진 정책 수단 ({len(inst)}개)</h2>
<p class="note">안건 제목을 정규화해 묶은 정책 수단 중에서 골랐다. 순위는 공개 규칙(의회 수, 제정 의회 수, 기간 중 신규 등장, 상향 신호)으로 정했다.
확산 단계와 6개월 신규 예상은 조례 확산 예측 모형의 결과다.</p>
{table(inst)}
<h2>발언에서만 나오는 정책 이름 ({len(prop)}개)</h2>
<p class="note">조례 제목에는 없지만 발언에 자주 나오는 정책 고유명사(카드, 패스, 바우처 등)다. 논의한 의회 수 순서다.
조례 안건이 없어 예측 모형의 대상이 아니며, 확산 단계는 논의 지표로 본 전망(규칙)이다.</p>
{table(prop)}</main></body></html>"""
