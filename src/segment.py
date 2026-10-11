"""회의록 평문에서 본문 범위, 머리말 정보, 안건, 발언을 분리한다.

모든 위치(start, end)는 html_to_text()가 돌려준 평문 기준의 문자 위치다.
그래서 분석 결과를 원문 구간으로 되짚을 때 text[start:end]로 그대로 꺼낼 수 있다.

발언자 표기는 의회 시스템에 따라 두 가지다.
  A형: '○위원장 홍길동 의석을 정돈하여…' 처럼 ○ 뒤에 직함·이름·발언이 한 줄에 이어진다.
  B형: '위원장 홍길동' 처럼 발언자만 한 줄에 있고 다음 줄부터 발언이 이어진다.
       (광주·인천·전남·전북 시스템. 전남은 '의장 홍 길 동'처럼 이름 글자 사이에 공백이 있다.)
문서마다 두 형식의 매칭 수를 비교해 많은 쪽을 쓴다.

2026-10-11 보강 (놓친 발언자 경계 약 10.5만 개, docs/10_도메인_난이도.md 1절):
  - 두 단어 이상의 직함: '○ 교육청 예산기획과장 최진욱' (부산)
  - 영문이 섞인 직함: '○메타AI과학국장 이정우', '○APEC준비지원단장 김상철' (경북)
  - '자'로 끝나는 직함: '○제주시장인사청문대상자 김완근' (제주·충북)
  - A형에서 띄어 쓴 이름: '○환경산림국장 구 상' (충남)
  - B형에서 이름과 직함이 붙은 줄: '박정희위원' (전북)
안건 목록이 개의 표시 뒤, 위원장 발언 안에 나오는 회의록(부산 2024년 4분기 이후)은
"안건을 상정…" 발화 바로 뒤의 번호 항목을 안건으로 읽는다.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# ---------------------------------------------------------------- 공통 패턴
NAME = r"[가-힣]{2,4}(?:\([^)\n]{1,12}\))?"          # 김성수(안양)
SPACED_NAME = r"[가-힣](?: [가-힣]){1,3}"             # 홍 길 동
ROLE_TOKEN = r"[가-힣A-Za-z·ㆍ().0-9]{1,24}?[장원관감사인행리표수문자]"
ROLE_WORD = r"[가-힣A-Za-z·ㆍ().0-9]{1,20}"                # 직함 앞에 붙는 기관명 (교육청 등)
ROLE = rf"(?:{ROLE_WORD} ){{0,2}}?{ROLE_TOKEN}(?: (?:직무대행|직무대리|대행|대리))?"
NAME_ROLE_SUFFIX = r"(?:부위원장|위원장|부의장|의장|의원|위원|교육감)"
COMPACT_ROLE = r"(?:부위원장|부의장|위원장|위원|의원|의장)"  # '박정희위원'처럼 이름에 붙어 쓰는 직함

# 이름 뒤 구분: 공백, 줄끝, '>'(서울 일부 '○재무국장 이상훈> 네.'). 직함 뒤 '(의석에서)' 허용(충남)
SPK_A = re.compile(
    rf"^○ ?(?:(?P<name2>{NAME}) (?P<role2>{NAME_ROLE_SUFFIX})(?:\([^)\n]{{1,10}}\))?"
    rf"|(?P<role>{ROLE}) (?P<name>{NAME}|{SPACED_NAME}))(?:[ >]|$)"
)
SPK_B = re.compile(
    rf"^(?:[▶↘→] ?)?(?:(?P<name2>{NAME}) (?P<role2>{NAME_ROLE_SUFFIX})|(?P<role>{ROLE}) (?P<name>{NAME}|{SPACED_NAME})"
    rf"|(?P<name3>[가-힣]{{2,4}}?)(?P<role3>{COMPACT_ROLE}))$"
)
# 개의 뒤 위원장 발언 안에서 안건 목록이 시작됨을 알리는 말
AGENDA_CUE = re.compile(r"안건을?\s*(?:일괄\s*)?상정|상정(?:토록|하도록|하겠습니다|합니다)")
SUB_ITEM = re.compile(r"^[가-하]\.\s")

# 본문 시작 단서: '일시', '일 시', '일자'로 시작하는 줄
DATE_LINE = re.compile(r"^(?:일 ?시|일 ?자)\s*[:：]?\s*\d{4}\s*년")
# '일시' 없이 날짜만 있는 줄 (충남·대구 등): 2024년6월10일(월) 14시
BARE_DATE_LINE = re.compile(r"^\d{4}\s*년\s*\d{1,2}\s*월\s*\d{1,2}\s*일\s*\([월화수목금토일]\)")
TITLE_START = re.compile(r"^﻿?\s*(?:제\s*\d+\s*회|\d{4}\s*년도)")
OPEN_MARK = re.compile(r"^\(\s*\d{1,2}\s*시\s*(?:\d{1,2}\s*분)?\s*(?:개의|개회|개식|감사\s*개시|개시|속개|조사\s*개시)\s*\)")
CLOSE_MARK = re.compile(r"\(\s*\d{1,2}\s*시\s*(?:\d{1,2}\s*분)?\s*(?:산회|폐회|폐식|감사\s*종료|감사\s*중지|종료|조사\s*종료)\s*\)")

SESSION = re.compile(r"제\s*(\d+)\s*회")
SESSION_TYPE = re.compile(r"(임시회|정례회)")
SITTING = re.compile(r"제\s*(\d+)\s*(?:호|차)")
COMMITTEE = re.compile(r"^(?:.*?의회\s*)?([가-힣·ㆍ\s]{2,30}?)\s*회의록")
AGENDA_ITEM = re.compile(r"^(\d{1,3})\.\s*(.+)$")

AGENDA_KINDS = [
    ("조례안", r"조례\s*(?:일부|전부)?\s*(?:개정|폐지|제정)?\s*조례안|조례안"),
    ("건의안", r"건의안"),
    ("결의안", r"결의안"),
    ("동의안", r"동의안"),
    ("예산·결산", r"예산안|결산|기금운용계획|추가경정"),
    ("행정사무감사", r"행정사무감사"),
    ("업무보고", r"업무보고|추진상황\s*보고|업무\s*보고"),
    ("5분자유발언", r"5분\s*자유발언"),
    ("시정질문", r"시정질문|도정질문|군정질문|교육행정질문|질문"),
    ("청원·진정", r"청원|진정"),
]


@dataclass
class Utterance:
    role: str
    name: str
    start: int       # 발언 본문 시작 위치(발언자 표기 제외)
    end: int
    head_start: int  # 발언자 표기 시작 위치


@dataclass
class Parsed:
    body_start: int = 0
    body_end: int = 0
    header: dict = field(default_factory=dict)
    agenda: list = field(default_factory=list)
    utterances: list = field(default_factory=list)
    spk_format: str = ""


def _lines_with_offsets(text: str):
    pos = 0
    for line in text.split("\n"):
        yield pos, line
        pos += len(line) + 1


def _clean_name(s: str) -> str:
    return re.sub(r"\s+", "", s)


def agenda_kind(title: str) -> str:
    for kind, pat in AGENDA_KINDS:
        if re.search(pat, title):
            return kind
    return "기타"


def parse(text: str) -> Parsed:
    p = Parsed(body_end=len(text))
    lines = list(_lines_with_offsets(text))

    # 1) 본문 시작: 첫 '일시' 줄에서 거슬러 올라가 제목 줄을 찾는다.
    date_i = next((i for i, (_, l) in enumerate(lines) if DATE_LINE.match(l.strip())), None)
    if date_i is None:
        date_i = next((i for i, (_, l) in enumerate(lines) if BARE_DATE_LINE.match(l.strip())), None)
    head_i = 0
    if date_i is not None:
        head_i = max(0, date_i - 4)
        for j in range(date_i, max(-1, date_i - 7), -1):
            if TITLE_START.match(lines[j][1].strip()):
                head_i = j
                break
    p.body_start = lines[head_i][0]

    # 2) 본문 끝: 마지막 산회·폐회 표기가 있는 줄의 끝
    closes = list(CLOSE_MARK.finditer(text, p.body_start))
    if closes:
        last = closes[-1]
        nl = text.find("\n", last.end())
        p.body_end = len(text) if nl < 0 else nl

    # 3) 머리말 정보 (제목 블록 = 본문 시작부터 '일시' 줄까지)
    hdr_end = lines[date_i][0] + len(lines[date_i][1]) if date_i is not None else p.body_start + 300
    hdr = text[p.body_start:hdr_end]
    m = SESSION.search(hdr)
    p.header["session"] = int(m.group(1)) if m else None
    m = SESSION_TYPE.search(hdr)
    p.header["session_type"] = m.group(1) if m else None
    m = SITTING.search(hdr)
    p.header["sitting"] = int(m.group(1)) if m else None
    comm = None
    for _, l in lines[head_i:(date_i or head_i) + 1]:
        mm = COMMITTEE.match(l.strip())
        if mm:
            comm = re.sub(r"\s+", "", mm.group(1))
            break
    p.header["committee"] = comm
    if date_i is not None:
        p.header["date_line"] = lines[date_i][1].strip()

    # 4) 안건: 제목 블록 뒤부터 첫 개의 표기 전까지의 번호 항목
    open_i = next((i for i in range(head_i, len(lines)) if OPEN_MARK.match(lines[i][1].strip())), None)
    stop_i = open_i if open_i is not None else min(len(lines), head_i + 80)
    seen = set()

    def add_item(i, mm):
        title = mm.group(2).strip()
        key = re.sub(r"\(.*?\)|\s", "", title)
        if key in seen:
            return
        seen.add(key)
        p.agenda.append(dict(no=int(mm.group(1)), title=title, kind=agenda_kind(title),
                             start=lines[i][0], end=lines[i][0] + len(lines[i][1])))

    for i in range(head_i, stop_i):
        mm = AGENDA_ITEM.match(lines[i][1].strip())
        if mm:
            add_item(i, mm)
    # 4-1) 개의 앞에 안건 목록이 없으면, 개의 뒤 60줄 안의 "안건을 상정…" 발화 바로 뒤 번호 항목을 읽는다
    if not p.agenda and open_i is not None:
        for i in range(open_i, min(len(lines), open_i + 60)):
            if not AGENDA_CUE.search(lines[i][1]):
                continue
            j = i + 1
            while j < len(lines) and j < i + 300:
                s = lines[j][1].strip()
                mm = AGENDA_ITEM.match(s)
                if mm:
                    add_item(j, mm)
                elif not (SUB_ITEM.match(s) or not s):
                    break
                j += 1
            if p.agenda:
                break

    # 5) 발언 분리
    body_lines = [(o, l) for o, l in lines if p.body_start <= o < p.body_end]
    hits_a, hits_b = [], []
    for o, l in body_lines:
        s = l.strip()
        lead = len(l) - len(l.lstrip())
        ma = SPK_A.match(s)
        if ma:
            hits_a.append((o + lead, o + lead + ma.end(), ma))
            continue
        mb = SPK_B.match(s)
        if mb:
            hits_b.append((o + lead, o + len(l) + 1, mb))
    use_b = len(hits_b) > len(hits_a)
    hits = hits_b if use_b else hits_a
    p.spk_format = "B" if use_b else "A"
    for k, (hs, ss, m) in enumerate(hits):
        end = hits[k + 1][0] if k + 1 < len(hits) else p.body_end
        g = m.groupdict()
        if g.get("name2"):
            role, name = g["role2"], g["name2"]
        elif g.get("name3"):
            role, name = g["role3"], g["name3"]
        else:
            role, name = g["role"], g["name"]
        p.utterances.append(Utterance(role=_clean_name(role), name=_clean_name(name),
                                      start=min(ss, end), end=end, head_start=hs))
    return p
