"""회의록 HTML을 줄 단위 텍스트로 바꾸는 함수."""
from __future__ import annotations

import re

import lxml.html

# 줄바꿈을 만들어야 하는 블록 태그
BLOCK_TAGS = {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6",
              "dt", "dd", "table", "ul", "ol", "td", "th", "section", "article"}


def html_to_text(html: str) -> str:
    """script/style을 버리고 블록 태그마다 줄을 바꾼 평문을 돌려준다."""
    if not html or not html.strip():
        return ""
    doc = lxml.html.fromstring(html)
    for bad in doc.xpath("//script|//style|//noscript|//head"):
        bad.drop_tree()
    for el in doc.iter():
        if isinstance(el.tag, str) and el.tag.lower() in BLOCK_TAGS:
            el.tail = ("\n" + el.tail) if el.tail else "\n"
    t = doc.text_content()
    t = t.replace("\r", "")
    t = re.sub(r"[ \t 　]+", " ", t)
    t = re.sub(r" *\n *", "\n", t)
    t = re.sub(r"\n{2,}", "\n", t)
    return t.strip()
