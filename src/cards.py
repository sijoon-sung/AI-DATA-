"""이슈 카드: 사건표에서 이슈 하나의 현황, 트렌드, 흐름, 쟁점, 도입 이유, 예측, 근거를 계산한다.

판정 규칙과 근거:
  - 현황 단계: 언급 / 실질 논의 / 상정 / 상임위 가결 / 본회의 가결 / 기존 조례(기간 안 첫 안건이 개정).
  - 가결: 회의록 본문의 선포 문장("…가결되었음을 선포합니다")을 안건 이름·항 번호·직전 문맥으로 이 안건에 연결한다(규칙 근사).
  - 근거 문단: 핵심 별칭으로 걸린 문단 전부 + 넓은 별칭으로만 걸린 문단 중 관련 점수(bge-reranker) REL_TAU 이상.
    핵심/넓은 별칭은 08단계가 별칭별 관련 비율로 정한다(core 열). 재순위 점수는 짧은 대화체 언급에도 낮게 나오므로
    문단 하나하나를 점수로 거르지 않고, 넓은 별칭이 끌어온 동명이의만 점수로 거른다.
  - 첫 언급: 근거 문단 중 가장 이른 것. 확인된 최초 관측: 관련 점수 REL_TAU 이상인 가장 이른 문단.
  - 근거 등급: E1 명시적 참조(다른 의회 이름 + 정책 단서 + 이슈 별칭이 가까이), E2 공통 법령(특정 법령 + 시행·위임 표현).
  - 이슈 유형: 법 대응형 / 참조 확산형 / 단일 의회 정책 + 사례 언급 / 근거 미확인 다지역형.
  - 쟁점: 이슈 문장을 bge-m3로 군집하고, 묶음마다 두드러진 명사와 대표 원문을 보인다(요약문을 새로 쓰지 않는다).
LLM은 쓰지 않는다. 모든 인용은 원문 문단의 일부이며 cite()가 글자 일치를 검사한다.
"""
from __future__ import annotations

import math
import re

import numpy as np
import pandas as pd
import pyarrow.dataset as ds

COUNCILS = ["서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종", "경기",
            "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주"]
COUNCIL_PAT = {
    "서울": r"서울(?:시|특별시)", "부산": r"부산(?:시|광역시)", "대구": r"대구(?:시|광역시)", "인천": r"인천(?:시|광역시)",
    "광주": r"광주광역시", "대전": r"대전(?:시|광역시)", "울산": r"울산(?:시|광역시)", "세종": r"세종(?:시|특별자치시)",
    "경기": r"경기도", "강원": r"강원(?:도|특별자치도)", "충북": r"충청북도|충북", "충남": r"충청남도|충남",
    "전북": r"전라북도|전북", "전남": r"전라남도|전남", "경북": r"경상북도|경북", "경남": r"경상남도|경남",
    "제주": r"제주(?:도|특별자치도)",
}
REL_TAU = 0.5          # 확인된 관측으로 볼 관련 점수. 넓은 별칭으로만 걸린 문단도 이 점수 이상이어야 쓴다
POLICY_CUE = re.compile(r"조례|사례|시행|도입|운영|만들|제정|벤치마킹|추진")
LAW = re.compile(r"「([^」]{2,40}(?:법|법률|시행령))」")
TRIGGER = re.compile(r"(?:시행|제정|개정|공포)(?:됨에|되어|되었|됨|에) ?따라|위임된")
GENERAL_LAWS = {"지방자치법", "지방재정법", "지방공무원법", "지방자치법 시행령", "지방교육자치에 관한 법률"}
EXISTING_CUE = re.compile(r"(?:저희|우리|본청|우리 도|우리 시)[^.?!]{0,40}?(?:이미|전국 최초로|벌써)\s?[^.?!]{0,30}?"
                          r"(?:만들었|제정했|제정하였|제정되었|제정돼|시행하고 있|운영하고 있)")
UPWARD_CUE = re.compile(r"(?:법률|법)\s?(?:제정|개정).{0,15}(?:촉구|건의|필요|요청)|국회.{0,20}(?:건의|촉구|입법)")
PROC_CUE = re.compile(r"상정|의사일정|선포|가결|제안설명|심사보고|검토보고|보고드리|보고입니다|의안번호|의결|토론 종결|이의 ?없|이의가 없"
                      r"|대표\s?발의|공동\s?발의|발의하신|발의한|발의해")
# 쟁점어에서 뺄 사람 이름: 흔한 성으로 시작하는 세 글자 고유명사(형태소 분석기가 이름을 고유명사로 태깅한다)
SURNAME = set("김이박최정강조윤장임한오서신권황안송류전홍고문양손배백허유남심노하곽성차주우구민진나지엄채원천방공현함변염여추도소석선설마길연위표명기반왕금옥육인맹제모탁국어은편용예봉경")
DECISION = re.compile(r"[^\n]{0,240}?(원안대로|수정안대로|수정한 부분은)?[^\n]{0,20}?(가결|부결|보류)[^\n]{0,30}")


def snip(text, pat, w=30):
    m = re.search(pat, text)
    if not m:
        return text[: 2 * w]
    a, z = max(0, m.start() - w), min(len(text), m.end() + w)
    return ("…" if a else "") + text[a:z].replace("\n", " ") + ("…" if z < len(text) else "")


def cite(row, quote, kind="발언"):
    core = quote.strip("…")
    ok = core in str(row.text).replace("\n", " ") if hasattr(row, "text") else None
    return {"council": row.council_short, "date": str(row.date.date()), "doc": row.mints_nm, "doc_id": row.doc_id,
            "role": getattr(row, "role", ""), "kind": kind, "quote": quote, "verified": ok,
            "rel": None if pd.isna(getattr(row, "rel", np.nan)) else round(float(row.rel), 2),
            "via": getattr(row, "source", "alias")}


# ---------------------------------------------------------------- 의결
def decisions(bills, alias, docs_path):
    b = bills[bills.act.isin(["제정", "개정", "폐지"])]
    if b.empty:
        return pd.DataFrame()
    tbl = ds.dataset(docs_path).to_table(columns=["doc_id", "text"], filter=ds.field("doc_id").isin(sorted(b.doc_id.unique())))
    texts = dict(zip(tbl.column("doc_id").to_pylist(), tbl.column("text").to_pylist()))
    out = []
    for r in b.itertuples():
        text = texts.get(r.doc_id, "")
        best = None
        for m in DECISION.finditer(text):
            line = m.group(0)
            if "선포" not in line and "되었습니다" not in line and "하겠습니다" not in line:
                continue
            how = None
            rg = re.search(r"제\s*(\d+)\s*항부터\s*제\s*(\d+)\s*항까지", line)
            one = re.search(r"의사일정\s*제\s*(\d+)\s*항", line)
            if re.search(alias, line):
                how = "제목 일치"
            elif rg and int(rg.group(1)) <= r.no <= int(rg.group(2)):
                how = "일괄 처리"
            elif one and int(one.group(1)) == r.no:
                how = "항 번호 일치"
            elif not rg and not one:
                ctx = text[max(0, m.start() - 600): m.start()]
                marks = [(x.end(), "alias") for x in re.finditer(alias, ctx)]
                marks += [(x.end(), int(x.group(1))) for x in re.finditer(r"제\s*(\d+)\s*항", ctx)]
                if marks and max(marks)[1] in ("alias", r.no):
                    how = "직전 문맥"
            if how:
                best = (m.group(2), how, line.strip()[-90:])
                if how != "일괄 처리":
                    break
        if best:
            out.append({"doc_id": r.doc_id, "council": r.council_short, "date": r.date, "plenary": r.plenary,
                        "result": best[0], "how": best[1], "line": best[2], "title": r.title, "act": r.act})
    return pd.DataFrame(out)


# ---------------------------------------------------------------- 현황표
def status_table(pas, bills, dec, alias):
    rows = []
    for c in COUNCILS:
        g = pas[pas.council_short == c]
        b = bills[(bills.council_short == c) & bills.act.isin(["제정", "개정", "폐지"])].sort_values("date")
        d = dec[dec.council == c] if len(dec) else pd.DataFrame()
        r = {"council": c, "n_passages": int(len(g)), "stage": "없음"}
        if len(g):
            f = g.iloc[0]
            r.update(first_date=str(f.date.date()), first=cite(f, snip(f.text, alias)))
            r["stage"] = "언급"
            conf = g[g.rel >= REL_TAU] if "rel" in g else g.iloc[0:0]
            if len(conf):
                cf = conf.iloc[0]
                r.update(confirmed_date=str(cf.date.date()), confirmed=cite(cf, snip(cf.text, alias)))
            cnt = g.groupby("doc_id").size()
            sub = g[(g.doc_id.map(cnt) >= 2) | (g.is_member & (g.n_chars >= 150))]
            if len(sub):
                r["sub_date"] = str(sub.iloc[0].date.date())
                r["stage"] = "실질 논의"
            ex = g[g.text.str.contains(EXISTING_CUE)]
            if len(ex):
                r["existing_claim"] = cite(ex.iloc[0], snip(ex.iloc[0].text, EXISTING_CUE.pattern))
        if len(b):
            fb = b.iloc[0]
            r.update(bill_date=str(fb.date.date()), bill_title=fb.title[:70], bill_act=fb.act)
            if not r.get("first_date") or r["first_date"] > r["bill_date"]:
                # 안건 제목이 별칭과 표기가 달라('전기자동차등 전용주차구역') 발언 문단이 안 걸린 경우: 안건 제목을 첫 언급 근거로 쓴다
                r.update(first_date=r["bill_date"], first={
                    "council": c, "date": r["bill_date"], "doc": getattr(fb, "mints_nm", ""), "doc_id": fb.doc_id, "role": "",
                    "kind": "안건 제목", "quote": fb.title, "verified": None, "rel": None})
                if r["stage"] == "없음":
                    r["stage"] = "언급"
            r["stage"] = "상정"
            if len(d):
                held = d[d.result.isin(["보류", "부결"])]
                if len(held):
                    h = held.iloc[0]
                    r["held"] = f'{h.result} {str(h.date.date())} 「{h.title[:40]}」'
                passed = d[d.result == "가결"]
                if len(passed[~passed.plenary]):
                    r["stage"] = "상임위 가결"
                    r["committee_pass"] = str(passed[~passed.plenary].date.min().date())
                if len(passed[passed.plenary]):
                    r["stage"] = "본회의 가결"
                    r["plenary_pass"] = str(passed[passed.plenary].date.min().date())
                    r["pass_how"] = passed[passed.plenary].iloc[0].how
            if fb.act == "개정":
                r["stage"] = "기존 조례"
        rows.append(r)
    return rows


# ---------------------------------------------------------------- 트렌드
def trend(pas, totals):
    t = totals.groupby("month").n.sum()
    hit = pas.groupby(pas.date.dt.to_period("M").astype(str)).size()
    months = [str(p) for p in pd.period_range("2024-01", "2025-12", freq="M")]
    nat = [{"month": m, "hits": int(hit.get(m, 0)), "per10k": round(10_000 * hit.get(m, 0) / max(t.get(m, 1), 1), 2)}
           for m in months]
    cm = pas.groupby(["council_short", pas.date.dt.to_period("M").astype(str)]).size()
    tot = totals.set_index(["council_short", "month"]).n
    grid = {c: [round(10_000 * cm.get((c, m), 0) / max(tot.get((c, m), 1), 1), 1) for m in months] for c in COUNCILS}

    def half(a, b):
        idx = [i for i, m in enumerate(months) if a <= m <= b]
        return 10_000 * sum(nat[i]["hits"] for i in idx) / max(sum(t.get(months[i], 0) for i in idx), 1)

    h = {k: round(half(a, b), 2) for k, (a, b) in {"2024H1": ("2024-01", "2024-06"), "2024H2": ("2024-07", "2024-12"),
                                                   "2025H1": ("2025-01", "2025-06"), "2025H2": ("2025-07", "2025-12")}.items()}
    change = (h["2025H2"] - h["2025H1"]) / h["2025H1"] * 100 if h["2025H1"] else float("nan")
    a, z = (h["2024H1"] + h["2024H2"]) / 2, (h["2025H1"] + h["2025H2"]) / 2
    yoy = (z - a) / a * 100 if a else float("nan")
    cq = [{"q": str(q), "councils": int(pas[pas.date.dt.to_period("Q") == q].council_short.nunique())}
          for q in pd.period_range("2024Q1", "2025Q4", freq="Q")]
    return {"months": months, "national": nat, "grid": grid, "halves": h, "peak": max(nat, key=lambda x: x["per10k"])["month"],
            "change_25h2_vs_25h1": round(change, 1), "yoy": round(yoy, 1), "councils_by_quarter": cq}


# ---------------------------------------------------------------- 흐름
FULLNAME = {"서울": "서울시", "부산": "부산시", "대구": "대구시", "인천": "인천시", "광주": "광주시", "대전": "대전시",
            "울산": "울산시", "세종": "세종시", "경기": "경기도", "강원": "강원도", "충북": "충청북도", "충남": "충청남도",
            "전북": "전라북도", "전남": "전라남도", "경북": "경상북도", "경남": "경상남도", "제주": "제주도"}
NLI_TAU = 0.5
REGION_WORDS = set(FULLNAME.values()) | {"서울특별시", "부산광역시", "대구광역시", "인천광역시", "광주광역시", "대전광역시", "울산광역시",
                                        "세종특별자치시", "강원특별자치도", "전북특별자치도", "제주특별자치도", "충청남도", "충청북도",
                                        "전라남도", "전라북도", "경상남도", "경상북도", "경기도", "광역시", "특별시", "특별자치도"}


def reference_candidates(pas, alias, nli=None):
    """E1 규칙 후보: 다른 의회 이름이 든 문장에 정책 단서와 이슈 별칭이 함께 있는 경우. nli가 있으면 각 후보에
    '○○시는 어떤 정책을 시행하고 있다'는 내용 가설의 함의 확률(nli)을 붙인다(거르지는 않는다. 검수 표본에도 쓴다)."""
    out, prem, hyp = [], [], []
    for r in pas.itertuples():
        sents = [(x.start(), x.end()) for x in re.finditer(r"[^.?!\n]+[.?!]?", r.text)]
        if not sents:
            continue
        for a, cp in COUNCIL_PAT.items():
            if a == r.council_short:
                continue
            for m in re.finditer(cp, r.text):
                # 지명이 든 문장에 정책 단서와 이슈 별칭이 함께 있어야 한다(앞뒤 문장까지 넓히면 '경기도가 더경기패스를…'이
                # 앞 문장의 '기후동행카드' 때문에 기후동행카드의 경기 참조로 잡혔다).
                # NLI 전제는 그 한 문장이다(문단 300자를 넣으면 KLUE-NLI 판정기가 거의 다 '중립'으로 판정했다: 94개 중 2개 통과).
                k = next((i for i, (s, e) in enumerate(sents) if s <= m.start() < e), None)
                if k is None:
                    continue
                one = r.text[sents[k][0]: sents[k][1]].strip()
                if POLICY_CUE.search(one) and re.search(alias, one):
                    out.append({**cite(r, one[:220] + ("…" if len(one) > 220 else "")), "to": a, "pid": getattr(r, "pid", None),
                                "sentence": one, "span": [m.start() - sents[k][0], m.end() - sents[k][0]]})
                    prem.append(one)
                    hyp.append(f"{FULLNAME[a]}는 어떤 정책을 시행하고 있다.")
                    break
    if out and nli is not None:
        ent = nli.nli_probs(prem, hyp)[:, 0]
        for o, p in zip(out, ent):
            o["nli"] = round(float(p), 3)
    return out


def references(pas, alias, nli=None):
    """E1 명시적 참조: 규칙 후보 중 NLI 함의 확률이 NLI_TAU 이상인 것(KLUE-NLI로 학습한 KoELECTRA, src/nli.py).
    돌려주는 값: (의회 쌍 목록, 쌍마다 가장 이른 예시)."""
    out = reference_candidates(pas, alias, nli)
    if nli is not None:
        out = [o for o in out if o["nli"] >= NLI_TAU]
    out = [{k: v for k, v in o.items() if k not in ("sentence", "span")} for o in out]
    df = pd.DataFrame(out)
    if df.empty:
        return [], []
    edges = (df.groupby(["council", "to"]).agg(n=("date", "size"), first=("date", "min")).reset_index()
             .sort_values("first").to_dict(orient="records"))
    return edges, df.sort_values("date").drop_duplicates(["council", "to"]).to_dict(orient="records")


def laws(pas, adopters):
    out = []
    for r in pas.itertuples():
        for m in LAW.finditer(r.text):
            name = re.sub(r"\s+", " ", m.group(1))
            if name in GENERAL_LAWS:
                continue
            out.append({**cite(r, snip(r.text, re.escape(m.group(0)), 25)), "law": name, "trigger": bool(TRIGGER.search(r.text))})
    df = pd.DataFrame(out)
    if df.empty:
        return [], None
    summ = (df.groupby("law").agg(n=("date", "size"), councils=("council", "nunique"), trig=("trigger", "sum"))
            .reset_index().sort_values(["councils", "n"], ascending=False))
    top = summ.iloc[0].to_dict()
    top["adopter_cover"] = len(set(df[df.law == top["law"]].council) & set(adopters))
    ex = df[(df.law == top["law"]) & df.trigger]
    top["example"] = (ex if len(ex) else df[df.law == top["law"]]).iloc[0].to_dict()
    return summ.head(5).to_dict(orient="records"), top


def issue_type(edges, top_law, n_adopters, has_bills=True):
    # 제안설명의 절반 이상이 유인물로 대체되어 회의록에 법령명이 잘 남지 않는다(docs/10 4절).
    if top_law and top_law["councils"] >= 3 and top_law["trig"] >= 2:
        return "법 대응형", (f"{top_law['councils']}개 의회의 회의록이 같은 법령(「{top_law['law']}」)을 인용하고, "
                           f"그중 {int(top_law['trig'])}건에 시행·위임 표현이 있다. 의회 간 확산으로 그리지 않는다")
    if not has_bills:
        # 발언 전용 정책 이름: 조례 안건이 원래 없으므로, 참조가 한 의회에 몰리는지로 가른다
        to = pd.Series([e["to"] for e in edges for _ in range(int(e["n"]))])
        if len(edges) >= 2 and to.value_counts(normalize=True).iloc[0] >= 0.6:
            c = to.value_counts().index[0]
            return "단일 의회 정책 + 사례 언급", f"다른 의회의 참조 문장 {len(to)}개 중 {to.value_counts().iloc[0]}개가 {c}의 정책을 가리킨다"
        if edges:
            return "참조 확산형", f"다른 의회의 정책을 언급한 문장이 {len(edges)}개 의회 쌍에서 있다(조례 안건은 없는 발언 전용 정책 이름)"
        return "근거 미확인 다지역형", "조례 안건이 없는 발언 전용 정책 이름이고, 의회 간 명시적 참조도 확인되지 않는다"
    if n_adopters <= 1 and edges:
        return "단일 의회 정책 + 사례 언급", "조례·안건이 한 곳 이하이고, 다른 의회는 사례로 언급한다"
    if edges:
        return "참조 확산형", f"다른 의회의 정책을 언급한 발언이 {len(edges)}개 의회 쌍에서 있다"
    return "근거 미확인 다지역형", "공통 법령도, 의회 간 명시적 참조도 확인되지 않는다"


# ---------------------------------------------------------------- 쟁점
def issue_clusters(pas, alias, stop, model, kiwi):
    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score
    src = pas
    rows = []
    for r in src.itertuples():
        for s in re.split(r"(?<=[.?!])\s+", str(r.text)):
            s = s.strip()
            if 25 <= len(s) <= 300 and re.search(alias, s) and not PROC_CUE.search(s):
                rows.append({"council": r.council_short, "date": r.date, "doc": r.mints_nm, "role": r.role,
                             "is_member": r.is_member, "s": s, "masked": re.sub(alias, "[이슈]", s)})
    sent = pd.DataFrame(rows).drop_duplicates("s").reset_index(drop=True) if rows else pd.DataFrame()
    if len(sent) < 30:
        return None
    if len(sent) > 3000:
        sent = sent.sample(3000, random_state=0).reset_index(drop=True)
    emb = model.encode(sent.masked.tolist(), batch_size=32, normalize_embeddings=True, show_progress_bar=False)
    best = None
    for k in range(4, 9):
        km = KMeans(n_clusters=k, n_init=10, random_state=0).fit(emb)
        sc = silhouette_score(emb, km.labels_, metric="cosine")
        if best is None or sc > best[0]:
            best = (sc, k, km)
    sc, k, km = best
    labels = km.labels_
    base_stop = {"부분", "관련", "생각", "말씀", "우리", "저희", "정도", "경우", "문제", "이번", "지금", "현재", "내용", "부서",
                 "해당", "위원", "의원", "질의", "답변", "그것", "이것", "사항", "때문", "거기", "여기", "하나", "필요", "확인",
                 "자료", "이제", "다음", "가지",
                 # 의사 절차어: 어느 이슈에나 나와 쟁점을 가리지 못한다
                 "발의", "조례", "조례안", "제정", "개정", "입안", "위임", "찬성", "보고", "참고", "의결", "심사", "검토",
                 "원안", "수정", "조항", "규정", "상정", "가결", "제안", "설명", "취지", "도민", "시민", "위원회",
                 "의안", "번호", "회의록", "지원", "관한", "의회", "대표", "페이지", "실장", "국장", "과장", "일부", "전체",
                 "얘기", "이야기", "숫자", "질문", "진행", "상태", "요청", "준비"} | stop | REGION_WORDS
    terms = []
    for c in range(k):
        toks = [t.form for s in sent.s[labels == c] for t in kiwi.tokenize(s)
                if t.tag in ("NNG", "NNP") and len(t.form) >= 2 and t.form not in base_stop
                and not (t.tag == "NNP" and len(t.form) == 3 and t.form[0] in SURNAME)]
        terms.append(pd.Series(toks, dtype=str).value_counts())
    allvc = pd.concat(terms).groupby(level=0).sum()
    N = allvc.sum()
    out = []
    for c in range(k):
        pos = np.where(labels == c)[0]
        g = sent.iloc[pos]
        vc, Nc = terms[c], max(terms[c].sum(), 1)
        score = {w: math.log((n / Nc) / (allvc[w] / N)) * math.log(1 + n) for w, n in vc.items()
                 if n >= 3 and (n / Nc) > (allvc[w] / N)}
        kw = [w for w, _ in sorted(score.items(), key=lambda x: -x[1])[:5]]
        cen = km.cluster_centers_[c] / np.linalg.norm(km.cluster_centers_[c])
        g = g.assign(sim=emb[pos] @ cen).sort_values("sim", ascending=False)
        reps, seen = [], set()
        for r in g.itertuples():
            if r.council in seen:
                continue
            seen.add(r.council)
            reps.append({"council": r.council, "date": str(r.date.date()), "doc": r.doc, "role": r.role,
                         "quote": r.s[:160] + ("…" if len(r.s) > 160 else "")})
            if len(reps) == 3:
                break
        out.append({"keywords": kw, "n_sent": int(len(g)), "n_councils": int(g.council.nunique()),
                    "member_share": round(float(g.is_member.mean()), 2), "reps": reps})
    out.sort(key=lambda x: (-x["n_councils"], -x["n_sent"]))
    return {"k": k, "silhouette": round(float(sc), 3), "n_sentences": int(len(sent)), "clusters": out}


# ---------------------------------------------------------------- 도입 이유, 상향 신호
def reasons(pas, bills, alias):
    out = []
    cand = pas[pas.doc_id.isin(set(bills.doc_id)) | pas.text.str.contains(r"제안\s?이유|제안설명|조례안을 제안")]
    for c, g in cand.groupby("council_short"):
        for r in g.itertuples():
            ss = [s.strip() for s in re.split(r"(?<=[.?!])\s+", r.text)
                  if re.search(r"위하여|위해|하고자|목적으로", s) and 20 <= len(s.strip()) <= 220
                  and (re.search(alias, s) or re.match(r"\s*(?:본|이)\s*(?:개정\s*|일부개정\s*)?(?:조례안|건의안)은", s))
                  and not PROC_CUE.search(s)]
            if ss:
                out.append({**cite(r, ss[0][:200]), "quote": ss[0][:200]})
                break
    return sorted(out, key=lambda x: x["date"])


def upward(pas, bills, alias):
    b = bills[bills.act.isin(["건의", "결의"])].copy()
    items = []
    if not b.empty:
        b["t"] = b.title.str.replace(r"\(.*?\)", "", regex=True).str.strip()
        b = b.sort_values("date").drop_duplicates(["council_short", "t"])
        items = [{"council": r.council_short, "date": str(r.date.date()), "title": r.t, "act": r.act} for r in b.itertuples()]
    # 상향 요구 표현이 이슈 별칭 가까이(앞뒤 150자) 있을 때만 센다. 여러 안건을 한꺼번에 보고하는 문단에서 다른 안건의 촉구를 잡지 않게 한다.
    near = re.compile(rf"(?:{alias})[^\n]{{0,150}}?(?:{UPWARD_CUE.pattern})|(?:{UPWARD_CUE.pattern})[^\n]{{0,150}}?(?:{alias})")
    talk = pas[pas.text.str.contains(near)]
    return {"bills": items, "talk_councils": int(talk.council_short.nunique()), "talk_n": int(len(talk)),
            "talk_example": cite(talk.iloc[0], snip(talk.iloc[0].text, near.pattern)) if len(talk) else None}


# ---------------------------------------------------------------- 예측 요약
def mention_outlook(status, tr):
    """논의 지표만으로 본 전망(모형이 아니다). 조례 안건 모형의 대상이 아닌 이슈에도 붙인다.
    규칙: 관련성 확인 의회 14곳 이상 = 포화, 2025 하반기 논의량이 상반기보다 30% 넘게 줄면 둔화,
    2025 하반기에 새로 논의를 시작한 의회가 2곳 이상이면 확산 중, 그 밖은 정체."""
    conf = [s["confirmed_date"] for s in status if s.get("confirmed_date")]
    new6 = sum(1 for d in conf if d >= "2025-07-01")
    ch = tr["change_25h2_vs_25h1"]
    ch = None if ch is None or (isinstance(ch, float) and math.isnan(ch)) else ch
    stage = ("포화" if len(conf) >= 14 else "둔화" if ch is not None and ch < -30
             else "확산 중" if new6 >= 2 else "정체")
    return {"stage": stage, "n_confirmed": len(conf), "new_2025h2": new6, "change": ch}


def forecast_view(fc_rows, fc_meta, status):
    if fc_rows is None or len(fc_rows) == 0:
        bills = [s for s in status if s.get("bill_date")]
        if fc_rows is not None and len(bills) == len(COUNCILS):   # 17곳 모두 안건을 내서 위험 집합이 비었다
            return {"origin": "2025-12-31", "b0": fc_meta["b0"], "grades": fc_meta["grades"],
                    "metrics": fc_meta.get("metrics", []), "n_any": len(bills),
                    "recent6": sum(1 for s in bills if s["bill_date"] >= "2025-07-01"), "stage": "포화",
                    "expected_new": 0.0, "interval80": [0, 0], "councils": []}
        return None
    existing = {s["council"] for s in status if s.get("existing_claim") and s["stage"] in ("언급", "실질 논의")}
    ps = fc_rows.p.to_numpy()
    sims = (np.random.default_rng(0).random((20_000, len(ps))) < ps).sum(1)
    lo, hi = np.percentile(sims, [10, 90])
    n_any, recent = int(fc_rows.n_any.iloc[0]), int(fc_rows.n_recent6.iloc[0])
    share = n_any / 17
    stage = "포화" if share >= 0.8 else "확산 중" if recent >= 2 else "둔화" if (share >= 0.3 and recent == 0) else "초기"
    return {"origin": "2025-12-31", "b0": fc_meta["b0"], "grades": fc_meta["grades"], "metrics": fc_meta.get("metrics", []),
            "n_any": n_any, "recent6": recent,
            "stage": stage, "expected_new": round(float(ps.sum()), 2), "interval80": [int(lo), int(hi)],
            "councils": [{"council_short": r.council_short, "p": float(r.p), "grade": r.grade,
                          "flag": "이미 만들었다는 발언 있음(확인 필요)" if r.council_short in existing else ""}
                         for r in fc_rows.sort_values("p", ascending=False).itertuples()]}


# ---------------------------------------------------------------- 카드
def build_card(spec, pas, bills, totals, docs_path, fc_rows, fc_meta, model, kiwi, nli=None):
    """pas: 별칭으로 찾은 후보 문단(rel, core 열 포함). 넓은 별칭으로만 걸리고 관련 점수가 REL_TAU 미만인 문단
    (이름만 같은 다른 이야기일 가능성이 큰 것)은 현황·트렌드·흐름·쟁점 계산에서 모두 뺀다. 후보 수는 n_candidates로 남긴다."""
    alias = spec["regex"]
    n_cand = int(len(pas))
    if "core" in pas:
        pas = pas[pas.core | (pas.rel >= REL_TAU)]
    dec = decisions(bills, alias, docs_path)
    status = status_table(pas, bills, dec, alias)
    tr = trend(pas, totals)
    edges, ref_ex = references(pas, alias, nli)
    adopters = sorted({s["council"] for s in status if s["stage"] in ("상정", "상임위 가결", "본회의 가결", "기존 조례")})
    law_summ, top_law = laws(pas, adopters)
    itype, why = issue_type(edges, top_law, len(adopters), has_bills=spec["kind"] == "inst")
    clus = issue_clusters(pas, alias, set(spec.get("stop", [])), model, kiwi)
    seen = [s for s in status if s.get("first_date")]
    first = min(seen, key=lambda s: s["first_date"]) if seen else None
    conf = [s for s in status if s.get("confirmed_date")]
    first_conf = min(conf, key=lambda s: s["confirmed_date"]) if conf else None
    early = sum(1 for s in seen if s["first_date"] <= "2024-03-31")
    n_c = len(seen)   # 발언 문단이나 안건 제목으로 이 이슈가 관측된 의회 수
    fc = forecast_view(fc_rows, fc_meta, status)
    if fc is None:
        fc_note = ("발언에서만 나오는 정책 고유명사라 조례 안건 기반 예측 모형의 대상이 아니다"
                   if spec["kind"] != "inst" else "기준점까지 제정 조례안이 한 건도 없어 예측 모형의 대상이 아니다")
    else:
        fc_note = ""
    return {
        "issue_id": spec["issue_id"], "kind": spec["kind"], "issue": spec["name"], "theme": spec.get("theme", ""),
        "title": spec["title"], "aliases": spec["aliases"], "alias_stats": spec.get("alias_stats", []),
        "n_candidates": n_cand, "n_passages": int(len(pas)), "n_councils": n_c,
        "n_semantic": int((pas.source == "semantic").sum()) if "source" in pas else 0,
        "left_censored": early >= max(3, n_c // 3), "n_early": early, "first": first, "first_confirmed": first_conf,
        "status": status, "trend": tr, "edges": edges, "ref_examples": ref_ex, "laws": law_summ, "top_law": top_law,
        "type": itype, "type_why": why, "adopters": adopters, "clusters": clus, "reasons": reasons(pas, bills, alias),
        "forecast": fc, "forecast_note": fc_note, "outlook": mention_outlook(status, tr), "upward": upward(pas, bills, alias),
        "bills": [{"council": r.council_short, "date": str(r.date.date()), "title": r.title, "act": r.act}
                  for r in bills.sort_values("date").itertuples()],
        "decisions": dec.assign(date=dec.date.astype(str)).to_dict(orient="records") if len(dec) else [],
    }
