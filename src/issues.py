"""L1 이슈 목록: 무엇을 셀 것인가.

두 출처에서 이슈를 만든다.
  1. 안건 제목(조례안·건의안·결의안): 제목을 정규화하고 bge-m3로 표기만 다른 같은 정책을 묶어 '정책 수단'을 만든다.
     정책 수단을 다시 넓게 묶어 '주제'를 만든다.
  2. 발언 전용 이슈: 안건 제목에는 없지만 여러 의회 발언에 나오는 정책 고유명사(○○카드, ○○패스, ○○교과서 등).
행정 정비성 조례(정원, 수수료, 직제, 공무원 보수 등)는 지방정책 이슈로 보지 않고 뺀다.
점수로 순위를 매겨 핵심 이슈를 고른다. 선정 규칙은 공개한다(docs/04_아키텍처.md 1단계).
"""
from __future__ import annotations

import os
import re
from collections import Counter

import numpy as np
import pandas as pd


COUNCILS = ["서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종", "경기",
            "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주"]
REGION = (r"(?:서울특별시|부산광역시|대구광역시|인천광역시|광주광역시|대전광역시|울산광역시|세종특별자치시|"
          r"경기도|강원특별자치도|강원도|충청북도|충청남도|전북특별자치도|전라북도|전라남도|경상북도|경상남도|"
          r"제주특별자치도)")
# 행정 정비성 안건: 지방정책 이슈가 아니라 기관 운영·정비에 관한 것
HOUSEKEEPING = re.compile(
    r"행정기구|정원|공무원|의정활동비|여비|보수|수수료|사용료|사무\s*위임|사무의\s*위임|위탁\s*사무|회의\s*규칙|의회\s*규칙|"
    r"직제|정비|명칭|복무|행동강령|윤리강령|공유재산|사무처|청사|포상|표창|인사|도세|시세|지방세|세\s*감면|"
    r"감면|과태료|위원회\s*(?:설치|구성)|출자|출연|금고|회계|기금\s*(?:설치|운용)|조례\s*폐지|시행\s*규칙|의회\s*기본|"
    r"공무국외|국외\s*출장|국외\s*연수|하자\s*관리|청렴|행정\s*심판|정보\s*공개|개인정보|기록물|자치법규|조직|사무\s*분장|"
    r"의정|의원\s*(?:윤리|행동|겸직|연구단체)|교섭단체|입법\s*평가|위탁\s*[·ㆍ‧]?\s*대행|공공기관\s*위탁"
)
# 한 단어로는 이슈라 하기 어려운 분야 이름(이 이름만 남는 정책 수단은 핵심 이슈에서 뺀다)
BROAD_SECTOR = {"관광진흥", "관광", "평생교육", "평생교육진흥", "문화재", "문화재보호", "체육", "산림", "농업", "어업", "수산",
                "도로", "하천", "주차장", "공원", "도서관", "박물관", "미술관", "보건", "의료", "식품", "위생", "청소년",
                "주택", "건축", "도시계획", "교통약자", "옥외광고물", "의용소방대"}
PARTICLE_TAIL = re.compile(r"(?<=[가-힣]{2})(?:의|을|를|과|와|에|등)$")
ADJ_TAIL = re.compile(r"(?:한|적|형|된|는|인|화)$")
GENERIC_TOKENS = {"지원", "육성", "조례", "관한", "대한", "및", "등", "활성화", "진흥", "설치", "운영", "관리", "조성",
                  "촉진", "보호", "증진", "기본", "개선", "강화", "추진", "위한", "의", "에", "사업", "계획", "시행", "제정",
                  "촉구", "건의안", "결의안", "건의", "결의", "반대", "대응", "마련", "개정", "법률", "법", "특별법", "국가",
                  "정부", "대책", "방안", "관련", "문제", "해결", "위한", "활용", "예방", "보전", "보존", "이용",
                  "사무", "피해", "대비", "안전한"}
TOO_BROAD = {"청년", "학생", "주민", "도민", "시민", "노인", "아동", "장애인", "여성", "농업", "교육", "문화", "관광",
             "환경", "복지", "안전", "주택", "교통", "건강", "체육", "산업", "경제", "학교", "지역", "가족", "어르신"}
# 발언 전용 이슈: 이름 끝이 이런 말인 정책 고유명사
PROPER_SUFFIX = r"(?:카드|패스|바우처|기본소득|페이(?!지)|쿠폰|교과서|아침밥|주택|돌봄)"
PROPER = re.compile(rf"(?<![가-힣A-Za-z0-9])([가-힣A-Za-z][가-힣A-Za-z0-9·\-]{{0,7}}{PROPER_SUFFIX})(?![가-힣])")
# 약한 접미어(주택, 돌봄, 카드)는 앞말이 일반어면 정책 고유명사가 아니다(청년주택, 긴급돌봄, 교통카드 등)
WEAK_SUFFIX = ("주택", "돌봄", "카드")
GENERIC_STEM = {"청년", "행복", "공공", "임대", "매입", "신혼", "노인", "주거", "긴급", "초등", "방과후", "아이", "가족", "지역",
                "통합", "공동", "교육", "일상", "아동", "영유아", "장애인", "가정", "마을", "학교", "보육", "온종일", "틈새",
                "체크", "신용", "교통", "법인", "선불", "직불", "충전", "복지", "전자", "모바일", "실물", "명함", "포인트",
                "기프트", "상품", "사업", "구매", "출입", "사원", "회원", "주민", "시민", "도민", "다자녀", "임산부", "어르신",
                "플래", "플랜", "레드", "옐로", "그린", "블루",
                # 주택 유형·정비 방식 (정책 이슈가 아니다)
                "연립", "다가구", "다세대", "국민", "분양", "가로", "기존", "일반", "단독", "공공분양", "통합공공임대",
                "청년임대", "공공지원민간임대", "장기전세", "민간임대", "전세", "월세", "노후",
                "할인", "관리", "자녀", "가사", "등록", "출입증"}
PROPER_STOP = {"신용카드", "체크카드", "교통카드", "하이패스", "법인카드", "카드", "패스", "주택", "보험", "수당", "돌봄",
               "공공주택", "임대주택", "건강보험", "고용보험", "산재보험", "의료보험", "국민건강보험", "보험료",
               "자동차보험", "공영주택", "민간주택", "단독주택", "공동주택", "노인주택", "농업인수당", "바우처", "쿠폰",
               "정당보험", "실업수당", "출장수당", "초과근무수당", "시간외수당", "명절수당", "직무수당", "위험수당",
               "특수근무수당", "가족수당", "보훈수당", "참전수당", "아동수당", "기초연금", "교과서", "검정교과서"}


# ---------------------------------------------------------------- 제목 정규화
def split_title(title: str) -> list[str]:
    """다른 안건과 붙은 제목('…조례안2. 전라남도 …')을 나눈다."""
    parts = re.split(r"(?<=[안건])\s?\d{1,2}\.\s", title)
    return [p.strip() for p in parts if p.strip()]


def act_of(t: str) -> str:
    if re.search(r"(?:일부|전부)개정조례안$", t):
        return "개정"
    if t.endswith("폐지조례안"):
        return "폐지"
    if t.endswith("조례안"):
        return "제정"
    if t.endswith("건의안"):
        return "건의"
    if t.endswith("결의안"):
        return "결의"
    return "기타"


def clean_title(t: str) -> tuple[str, str]:
    """(정책 이름, 형태). 예: '충청북도교육청 경계선 지능 학생 지원 조례안' → ('경계선 지능 학생 지원', '제정')."""
    t = re.sub(r"\([^()]*\)", "", t)
    t = re.sub(r"\([^()]*\)", "", t).strip()   # 괄호 안 괄호
    t = re.sub(r"\s*(?:심사의\s*)?(?:의\s*)?건$", "", t)
    act = act_of(t)
    if act == "기타":
        return "", act
    t = re.sub(r"(?:조례\s*)?(?:등\s*)?(?:일부개정|전부개정|폐지)?\s*조례안$|건의안$|결의안$", "", t)
    t = re.sub(rf"^{REGION}\s*(?:교육청|의회)?\s*", "", t)
    t = re.sub(r"(?:에\s*관한|에\s*대한)\s*$", "", t.strip())
    t = re.sub(r"\s+", " ", t).strip(" ·,")
    return t, act


def core_tokens(name: str) -> list[str]:
    toks = re.split(r"[\s·,]+", re.sub(r"(?:에\s*관한|에\s*대한|을\s*위한|를\s*위한)", " ", name))
    toks = [PARTICLE_TAIL.sub("", x) for x in toks]
    return list(dict.fromkeys(x for x in toks if x and x not in GENERIC_TOKENS and len(x) >= 2))


def alias_regex(alias: str) -> str:
    """띄어쓰기와 상관없이 찾는 정규식. '경계선지능' → '경\\s*계\\s*선\\s*지\\s*능'."""
    chars = [re.escape(c) for c in re.sub(r"\s+", "", alias)]
    return r"\s*".join(chars)


def aliases_from_names(names: list[str], token_freq: Counter | None = None) -> list[str]:
    """정책 이름들에서 검색용 별칭을 만든다.
    - 앞의 두 핵심어를 붙인 말('도심 복합개발' → '도심복합개발', '경계선 지능 학생' → '경계선지능')
    - 정책 이름 전체에서 드물게 쓰이는(3개 이름 이하) 4글자 이상 핵심어('자연유산', '자율소방대')
    너무 넓은 한 단어(청년, 학생, 전통시장처럼 여러 정책에 두루 쓰이는 말)는 홀로 별칭이 되지 않는다."""
    token_freq = token_freq or Counter()
    out = []
    for n in names:
        toks = core_tokens(n)
        if not toks:
            continue
        if len(toks) == 1:
            cand = [toks[0]]
        else:
            first = toks[0]
            cand = ["".join(toks[:2])] if (ADJ_TAIL.search(first) or len(first) <= 3 or first in TOO_BROAD
                                           or token_freq.get(first, 0) > 3) else [first, "".join(toks[:2])]
        cand += [t for t in toks if len(t) >= 4 and t not in TOO_BROAD and token_freq.get(t, 0) <= 3]
        out += [a for a in cand if len(a) >= 3 and a not in TOO_BROAD and a not in BROAD_SECTOR]
    return list(dict.fromkeys(out))[:6]


# ---------------------------------------------------------------- 안건 → 정책 수단
def bill_rows(ag: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for r in ag[ag.kind.isin(["조례안", "건의안", "결의안"])].itertuples():
        for part in split_title(r.title):
            name, act = clean_title(part)
            if not name or act == "기타":
                continue
            rows.append(dict(doc_id=r.doc_id, no=r.no, council_short=r.council_short, date=r.date,
                             plenary=r.plenary, mints_nm=getattr(r, "mints_nm", ""), title=part, name=name, act=act,
                             housekeeping=bool(HOUSEKEEPING.search(name))))
    return pd.DataFrame(rows)


def embed(texts, model=None, batch_size=64):
    import torch
    from sentence_transformers import SentenceTransformer
    dev = "cuda" if torch.cuda.is_available() else "cpu"  # GPU가 없으면 CPU로 (느리다)
    m = model or SentenceTransformer("BAAI/bge-m3", device=dev,
                                     model_kwargs={"torch_dtype": torch.float16 if dev == "cuda" else torch.float32})
    m.max_seq_length = 128
    return m.encode(list(texts), batch_size=batch_size, normalize_embeddings=True, show_progress_bar=False), m


def cluster(emb, threshold):
    from sklearn.cluster import AgglomerativeClustering
    if len(emb) < 2:
        return np.zeros(len(emb), dtype=int)
    return AgglomerativeClustering(n_clusters=None, metric="cosine", linkage="average",
                                   distance_threshold=threshold).fit(emb).labels_


def instruments(bills: pd.DataFrame, model=None, inst_thr=0.12, theme_thr=0.35):
    """정책 이름을 묶어 정책 수단과 주제를 만든다. bills에 inst_id 열을 더해 돌려준다."""
    pol = bills[~bills.housekeeping].copy()
    names = sorted(pol.name.unique())
    emb, model = embed(names, model)
    lab = cluster(emb, inst_thr)
    nm2inst = dict(zip(names, lab))
    pol["inst_id"] = pol.name.map(nm2inst)
    # 정책 수단 표
    rows = []
    for iid, g in pol.groupby("inst_id"):
        enact = g[g.act == "제정"]
        rows.append(dict(
            # 이름은 자주 쓰인 순서로 둔다. 첫 이름에서 나온 별칭이 대표 별칭이 된다(events.scan의 넓은 별칭 판정 기준)
            inst_id=int(iid), name=Counter(g.name).most_common(1)[0][0], names=[n for n, _ in Counter(g.name).most_common()],
            n_councils=g.council_short.nunique(), n_enact=enact.council_short.nunique(),
            n_upward=g[g.act.isin(["건의", "결의"])].council_short.nunique(),
            councils=sorted(g.council_short.unique()), first=g.date.min(), first_enact=enact.date.min(),
            acts=dict(Counter(g.act)),
        ))
    inst = pd.DataFrame(rows)
    # 주제: 정책 수단 대표 이름을 넓게 묶는다
    rep = inst.name.tolist()
    remb = emb[[names.index(n) for n in rep]]
    tl = cluster(remb, theme_thr)
    inst["theme_id"] = tl
    # 주제 이름: 묶음 안 정책 이름의 절반 이상에 나오는 핵심어가 있을 때만 붙인다(없으면 비운다)
    theme_name = {}
    for t, g in inst.groupby("theme_id"):
        if len(g) < 2:
            theme_name[t] = ""
            continue
        toks = Counter(tok for n in g.name for tok in set(core_tokens(n)))
        best = [w for w, c in toks.most_common() if c >= max(2, len(g) / 2) and len(w) >= 2]
        theme_name[t] = best[0] if best else ""
    inst["theme"] = inst.theme_id.map(theme_name)
    token_freq = Counter(tok for n in names for tok in set(core_tokens(n)))
    inst["aliases"] = [aliases_from_names(n, token_freq) for n in inst.names]
    inst["broad"] = [all(t in BROAD_SECTOR or t in TOO_BROAD for t in core_tokens(n)) for n in inst.name]
    return pol, inst, model


# ---------------------------------------------------------------- 발언 전용 이슈
def proper_noun_candidates(passages_path, docs, title_text: str, min_councils=3, min_passages=20):
    """발언에서 정책 고유명사 후보를 센다. 안건 제목에 이미 있는 이름은 뺀다."""
    import pyarrow.parquet as pq
    meta = docs.set_index("doc_id")[["council_short", "date"]]
    cnt, cset, first = Counter(), {}, {}
    pf = pq.ParquetFile(passages_path)
    for b in pf.iter_batches(columns=["doc_id", "text"], batch_size=200_000):
        ids = b.column("doc_id").to_pylist()
        for did, t in zip(ids, b.column("text").to_pylist()):
            if did not in meta.index:
                continue
            found = set(m.group(1) for m in PROPER.finditer(t))
            if not found:
                continue
            c, d = meta.at[did, "council_short"], meta.at[did, "date"]
            for w in found:
                w = re.sub(r"[-·]", "", w)
                if w in PROPER_STOP or len(w) < 3:
                    continue
                suf = re.search(PROPER_SUFFIX + "$", w)
                stem = w[: suf.start()] if suf else w
                if stem in GENERIC_STEM or (suf and suf.group(0) in WEAK_SUFFIX and len(stem) < 2):
                    continue
                cnt[w] += 1
                cset.setdefault(w, Counter())[c] += 1
                if w not in first or d < first[w]:
                    first[w] = d
    rows = []
    for w, n in cnt.items():
        cs = cset[w]
        if len(cs) < min_councils or n < min_passages:
            continue
        if re.sub(r"\s", "", w) in title_text:
            continue
        top_c, top_n = cs.most_common(1)[0]
        rows.append(dict(name=w, n_passages=n, n_councils=len(cs), top_council=top_c, top_share=top_n / n,
                         first=first[w], councils=dict(cs)))
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    # 점수(공개 규칙): 의회 수 + 기간 중 신규 등장 3점 + 한 의회에 몰린 지역 브랜드(절반 이상) 3점 + log(문단 수)
    out["novel"] = (out["first"] >= pd.Timestamp("2024-04-01")).astype(int)
    out["local_brand"] = (out.top_share >= 0.5).astype(int)
    out["score"] = out.n_councils + 3 * out.novel + 3 * out.local_brand + np.log1p(out.n_passages)
    return out.sort_values("score", ascending=False)


# ---------------------------------------------------------------- 핵심 이슈 선정
def score_instruments(inst: pd.DataFrame) -> pd.DataFrame:
    """공개 규칙: 새로 제정한 의회 수 + 0.3 × (개정 등 그 밖의 안건만 낸 의회 수) + 기간 중 신규(2024-04 이후 첫 제정) 2점
    + 상향 신호(건의·결의안) 1점. 기존 조례의 개정만 있는 수단(법 개정 반영 등)보다 새로 퍼진 수단을 앞에 둔다."""
    s = inst[~inst.broad].copy()
    s["novel"] = (s.first_enact >= pd.Timestamp("2024-04-01")).astype(int)
    s["score"] = s.n_enact + 0.3 * (s.n_councils - s.n_enact) + 2 * s.novel + (s.n_upward > 0).astype(int)
    return s.sort_values("score", ascending=False)
