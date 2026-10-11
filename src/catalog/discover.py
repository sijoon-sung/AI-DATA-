"""정책 카탈로그 A단계: 회의록에서 정책 이름 후보를 찾는다(손으로 만든 이름 목록 없이).

방법
  1. 문단을 어절로 나누고 앞뒤 문장부호와 끝의 조사를 뗀 '말'을 만든다(일반 문법 규칙만 쓴다).
  2. 말마다 의회별 등장 문단 수를 센다. 새 회의록이 들어오면 그 문단만 세어 더한다(count_batch → merge).
  3. 점수
     - 집중도: 가장 많이 쓴 의회의 비중. 지역 브랜드(동백전, 이응패스 등)는 한 의회에 몰린다.
     - 정책 맥락 비율: 그 말이 나온 문단 중 정책 일반어(사업·지원·예산·조례·발급·가맹·이용·혜택 등)가 함께 있는 비율.
     - 사전 여부: Kiwi 형태소 분석에서 일반 명사 하나로 끝나는 흔한 말(예산, 학생)은 뺀다. 복합어와 미등록어는 남긴다.
  4. 후보는 B단계(LLM 정책 프로필)로 넘긴다. 이 단계는 '정책인가'를 판정하지 않는다. 지명·기관명도 섞여 있다.
본보기: Evaporate(Arora et al., PVLDB 2023), LOTUS(Patel et al. 2024)처럼 싼 단계가 후보를 거르고 LLM은 좁은 집합에만 쓴다.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc

EDGE = r"^[\"'“”‘’「」『』()\[\]<>《》〈〉·,.?!:;~…]+|[\"'“”‘’「」『』()\[\]<>《》〈〉·,.?!:;~…]+$"
JOSA = (r"(?:으로는|로는|에서는|에서도|에게는|이라는|라는|이라고|라고|이라든지|라든지|이나|이랑|하고|처럼|보다|까지|부터|"
        r"에서|에게|으로|과의|와의|에는|에도|이며|이고|이다|입니다|이에요|예요|은|는|이|가|을|를|에|의|와|과|로|도|만|나|랑)$")
POLICY_CUE = r"사업|지원|예산|조례|발급|가맹|이용|혜택|도입|시행|운영|확대|정책|제도|신청|지급|할인|환급|충전|사용"
TOKEN_OK = r"^[가-힣A-Za-z][가-힣A-Za-z0-9·\-]{1,13}$"


def count_batch(doc_ids: pa.Array, texts: pa.Array, council_of: dict) -> pd.DataFrame:
    """문단 묶음 하나에서 (말, 의회)별 등장 문단 수와 정책 맥락 문단 수를 센다(문단 하나에 같은 말은 한 번)."""
    cue = pc.match_substring_regex(texts, POLICY_CUE)
    words = pc.utf8_split_whitespace(texts)
    flat = pc.list_flatten(words)
    parent = pc.list_parent_indices(words)
    w = pc.replace_substring_regex(flat, EDGE, "")
    w = pc.replace_substring_regex(w, JOSA, "")
    ok = pc.match_substring_regex(w, TOKEN_OK)
    w, parent = pc.filter(w, ok), pc.filter(parent, ok)
    t = pa.table({"w": w, "p": parent})
    t = t.group_by(["w", "p"]).aggregate([])                       # 문단 안 중복 제거
    p = t.column("p").to_numpy()
    council = np.asarray([council_of.get(d, "") for d in doc_ids.to_pylist()], dtype=object)[p]
    df = pd.DataFrame({"w": t.column("w").to_numpy(zero_copy_only=False), "council": council,
                       "cue": cue.to_numpy(zero_copy_only=False)[p]})
    return df.groupby(["w", "council"]).agg(n=("cue", "size"), n_cue=("cue", "sum")).reset_index()


def merge(parts: list[pd.DataFrame]) -> pd.DataFrame:
    return pd.concat(parts).groupby(["w", "council"], as_index=False)[["n", "n_cue"]].sum()


NOMINAL = {"NNG", "NNP", "NNB", "SL", "SN", "SH", "XPN", "XSN", "XR", "NR"}
SURNAME = set("김이박최정강조윤장임한오서신권황안송류전홍고문양손배백허유남심노하곽성차주우구민진나지엄채원천방공현함변염여추도소석선설마길연위표명기반왕금옥육인맹제모탁국어은편용예봉경")
PLACE_END = ("시", "도", "군", "구", "청", "읍", "면", "동", "리", "회", "원", "부", "처", "국", "과", "실", "소", "단")


def shape(kiwi, w: str) -> str:
    """말의 형태: 'name'(복합어·미등록어·외국어가 섞인 명사구), 'common'(사전의 일반 명사 하나), 'place'(지명·기관),
    'person'(사람 이름), 'other'(명사구가 아님: 동사·어미·부사 등)."""
    toks = kiwi.tokenize(w)
    if not toks or any(t.tag not in NOMINAL for t in toks):
        return "other"
    if len(toks) == 1 and toks[0].tag == "NNG":
        return "common"
    if toks[0].tag == "NNP" and len(toks) == 1 and len(w) == 3 and w[0] in SURNAME:
        return "person"
    if toks[0].tag == "NNP" and w.endswith(PLACE_END):
        return "place"
    return "name"


def score(counts: pd.DataFrame, kiwi=None, min_total=15) -> pd.DataFrame:
    """후보 점수 = 정책 맥락 비율 × log(등장 문단 수), 한 의회 집중(≥0.8)이면 1.5배.
    (점수는 LLM에 넘길 순서를 정할 뿐이다. 정책인지는 B단계가 판정한다.)"""
    g = counts.groupby("w")
    s = pd.DataFrame({"total": g.n.sum(), "n_cue": g.n_cue.sum(), "n_councils": g.council.nunique()})
    top = counts.sort_values("n", ascending=False).drop_duplicates("w").set_index("w")
    s["top_council"], s["top_n"] = top.council, top.n
    s = s[s.total >= min_total]
    s["concentration"] = (s.top_n / s.total).round(3)
    s["policy_ctx"] = (s.n_cue / s.total).round(3)
    if kiwi is not None:
        s["shape"] = [shape(kiwi, x) for x in s.index]
    s["score"] = (s.policy_ctx * np.log1p(s.total) * np.where(s.concentration >= 0.8, 1.5, 1.0)).round(3)
    return s.drop(columns=["top_n", "n_cue"]).sort_values("score", ascending=False)
