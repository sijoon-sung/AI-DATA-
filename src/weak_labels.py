"""L2 약지도 라벨 규칙.

규칙은 확신할 수 있는 경우에만 라벨을 붙이고, 애매하면 None(판단 보류)을 돌려준다.
보류된 표본과 규칙 라벨의 일부를 사람이 검수해 정답셋을 만든다.

과제
  (a) proc  : PROC(의사진행) / SUB(정책 논의)
  (c) ref   : 다른 시도를 언급한 문단의 성격
              POLICY_REF(정책 참조) / COMPARE(단순 비교) / COOP(협력) / OTHER(그 밖)
  (d) topdown: TOPDOWN(상위법·중앙정부 요인에 따른 논의) / 보류
"""
from __future__ import annotations

import re

# ---------------------------------------------------------------- 지역 사전
# 이름 뒤에 올 수 있는 말: 행정단위 접미사, 조사, 구두점, 공백
_TAIL = r"(?=특별시|광역시|특별자치시|특별자치도|시|도|의|은|는|이|가|에|과|와|을|를|처럼|보다|만|부터|까지|[\s,·ㆍ)\]」』'\"]|$)"
REGION_PATTERNS = {
    "서울": r"서울",
    "부산": r"부산(?!물)",
    "대구": r"대구",
    "인천": r"인천",
    "광주": r"광주",
    "대전": r"대전(?!환|제|략|쟁|투|차)",
    "울산": r"울산",
    "세종": r"세종(?=시|특별자치시)",       # '세종대왕', '세종문화회관' 제외
    "경기": r"경기도",                       # '경기'만으로는 경제 '경기'와 구분 불가
    "강원": r"강원",
    "충북": r"충청북도|충북",
    "충남": r"충청남도|충남",
    "전북": r"전라북도|전북",
    "전남": r"전라남도|전남",
    "경북": r"경상북도|경북",
    "경남": r"경상남도|경남",
    "제주": r"제주",
}
REGION_RE = {k: re.compile(rf"(?<![가-힣])(?:{v}){_TAIL}") for k, v in REGION_PATTERNS.items()}
GENERIC_OTHER = re.compile(r"타\s?시[·ㆍ]?도|다른\s?시[·ㆍ]?도|타\s?지자체|다른\s?지자체|타\s?광역|다른\s?광역|타\s?지역|다른\s?지역|전국\s?최초|전국\s?처음")


def find_regions(text: str, self_short: str | None = None):
    """문단 안의 다른 시도 언급 [(시도, start, end)]. 자기 지역은 뺀다."""
    out = []
    for k, rx in REGION_RE.items():
        if k == self_short:
            continue
        for m in rx.finditer(text):
            out.append((k, m.start(), m.end()))
    return sorted(out, key=lambda x: x[1])


# ---------------------------------------------------------------- (a) 의사진행
CHAIR_ROLES = re.compile(r"위원장|의장|부의장|직무대리|직무대행|위원장대리|사회")
PROC_PHRASES = re.compile(
    r"의석을\s?정돈|성원이\s?되었으므로|개의하겠습니다|개회하겠습니다|상정합니다|의사봉|산회를\s?선포|"
    r"정회를\s?선포|속개하겠습니다|질의하실\s?위원|질의하실\s?의원|이의\s?없으십니까|가결되었음을\s?선포|"
    r"수고하셨습니다|다음은\s?.{0,20}순서|발언대로\s?나오|나오셔서|마치도록\s?하겠습니다|회의를\s?마치|"
    r"의결하고자\s?하는데|그렇게\s?의결|선포합니다|자리에\s?앉아"
)


def label_proc(role: str, text: str) -> str | None:
    n = len(text)
    chair = bool(CHAIR_ROLES.search(role or ""))
    hits = len(PROC_PHRASES.findall(text))
    if chair and hits >= 1 and n < 200:
        return "PROC"
    if hits >= 2 and n < 150:
        return "PROC"
    if not chair and hits == 0 and n >= 150:
        return "SUB"
    return None


# ---------------------------------------------------------------- (c) 타 지역 언급의 성격
REF_POLICY = re.compile(r"조례|제도|정책|사업|사례|도입|시행|운영하고|벤치마킹|선도|추진하고|이미|먼저|모범|선진|우수\s?사례|따라서\s?만들|참고")
REF_COMPARE = re.compile(r"비교|대비|보다|전국\s?평균|순위|위를\s?차지|번째|꼴찌|최하위|최상위|최고|최저|%|퍼센트|배\s|격차")
REF_COOP = re.compile(r"협력|공동|협약|MOU|업무협약|연계|공조|상생|함께|연합|광역교통|메가시티|초광역|행정통합|통합")


def label_ref(text: str, regions) -> str | None:
    """다른 시도를 언급한 문단에만 쓴다. 규칙이 하나만 뚜렷하면 그 라벨, 아니면 보류."""
    if not regions:
        return None
    # 지역명 주변 ±60자 안의 단서만 본다
    hits = {"POLICY_REF": 0, "COMPARE": 0, "COOP": 0}
    for _, s, e in regions:
        w = text[max(0, s - 60):e + 60]
        hits["POLICY_REF"] += bool(REF_POLICY.search(w))
        hits["COMPARE"] += bool(REF_COMPARE.search(w))
        hits["COOP"] += bool(REF_COOP.search(w))
    on = [k for k, v in hits.items() if v > 0]
    if len(on) == 1:
        return on[0]
    if not on:
        return "OTHER"
    return None


# ---------------------------------------------------------------- (d) 하향 요인
TOPDOWN = re.compile(
    r"법\s?개정에\s?따라|법률\s?개정|법령\s?개정|상위\s?법|시행령\s?개정|시행규칙\s?개정|개정됨에\s?따라|"
    r"법\s?시행에\s?따라|법이\s?시행|의무화|정부\s?지침|정부\s?방침|중앙정부|국정과제|정부\s?정책에\s?따라|"
    r"부처\s?지침|표준\s?조례|표준조례|국비\s?공모|국가\s?공모|정부\s?공모"
)


def label_topdown(text: str) -> str | None:
    return "TOPDOWN" if TOPDOWN.search(text) else None
