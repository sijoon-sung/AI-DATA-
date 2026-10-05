"""L1: 발언을 모델 입력 단위인 문단(passage)으로 나눈다.

발언이 길면 문장 경계에서 잘라 MAX_CHARS 안팎의 문단 여러 개로 나눈다.
문단의 start, end는 docs.text 기준 문자 위치이므로 원문 구간을 그대로 꺼낼 수 있다.
"""
from __future__ import annotations

import re

MAX_CHARS = 400
# 문장 끝: 마침표·물음표·느낌표 뒤 공백, 또는 줄바꿈
SENT_END = re.compile(r"(?<=[.?!])\s+|\n+")


def split_utterance(text: str, start: int, end: int, max_chars: int = MAX_CHARS):
    """text[start:end]를 문단 (s, e) 목록으로 나눈다. 앞뒤 공백은 범위에서 뺀다."""
    seg = text[start:end]
    # 앞뒤 공백 제거에 맞춰 범위 조정
    lead = len(seg) - len(seg.lstrip())
    trail = len(seg) - len(seg.rstrip())
    s0, e0 = start + lead, end - trail
    if e0 <= s0:
        return []
    if e0 - s0 <= max_chars:
        return [(s0, e0)]
    # 문장 단위 경계 수집
    bounds, pos = [], s0
    for m in SENT_END.finditer(text, s0, e0):
        if m.start() > pos:
            bounds.append((pos, m.start()))
        pos = m.end()
    if pos < e0:
        bounds.append((pos, e0))
    # 문장을 이어 붙여 max_chars를 넘기 직전에 끊는다
    out, cs, ce = [], None, None
    for bs, be in bounds:
        if cs is None:
            cs, ce = bs, be
        elif be - cs <= max_chars:
            ce = be
        else:
            out.append((cs, ce))
            cs, ce = bs, be
    if cs is not None:
        out.append((cs, ce))
    # 한 문장이 아주 길면 글자 수로 강제 분할
    final = []
    for a, b in out:
        while b - a > max_chars * 2:
            final.append((a, a + max_chars))
            a += max_chars
        final.append((a, b))
    return final
