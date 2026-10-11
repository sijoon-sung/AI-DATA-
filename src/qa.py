"""근거 기반 질의응답: 이슈 카드(구조화된 사실)와 근거 문단에서 답하고, 생성한 문장은 하나씩 검증한다.

흐름
  1. 이해: 질문에서 이슈(별칭 일치 → 없으면 bge-m3 유사도), 의회, 질문 유형을 찾는다. 이슈를 못 찾으면 답하지 않는다.
  2. 근거 모으기: 질문 유형에 맞는 카드의 사실을 번호 붙은 근거 [n]으로 만든다(템플릿 문장 + 원문 인용).
     '○○의회는 뭐라고 했나' 같은 질문은 그 이슈의 근거 문단을 교차 인코더로 다시 순위를 매겨 원문을 근거로 붙인다.
  3. 답 만들기: 기본은 템플릿 답(결정적). --llm이면 로컬 Qwen2.5-7B가 근거 번호를 달아 문장을 쓴다.
  4. 검증(생성한 문장마다): (a) 인용 번호가 있고 실제 근거를 가리키는가, (b) 문장의 날짜·숫자·의회 이름이 인용한 근거에
     있는가, (c) 인용한 근거의 문장 하나라도 생성 문장을 함의하는가(KLUE-NLI KoELECTRA, 문장 단위 전제).
     통과한 문장만 남긴다. 남은 문장이 없거나 핵심 사실이 빠지면 템플릿 답으로 돌아가고, 근거가 없으면 답하지 않는다.

본보기: ALCE(Gao et al. 2023)의 인용 재현율·정밀도(NLI로 인용이 문장을 뒷받침하는지 판정), RARR(Gao et al. 2023)의
'생성 뒤 근거로 고치기', 그리고 이 프로젝트에서 확인한 사실 — NLI 전제는 한 문장 단위여야 판정이 된다.
LLM은 근거를 문장으로 옮기는 데만 쓴다. 숫자·날짜·순서는 카드(코드가 계산한 값)에서만 온다.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CARDS = ROOT / "results" / "issue_cards"
P = ROOT / "data" / "processed"
COUNCIL_WORDS = {
    "서울": r"서울", "부산": r"부산", "대구": r"대구", "인천": r"인천", "광주": r"광주", "대전": r"대전", "울산": r"울산",
    "세종": r"세종", "경기": r"경기도?", "강원": r"강원", "충북": r"충북|충청북도", "충남": r"충남|충청남도",
    "전북": r"전북|전라북도", "전남": r"전남|전라남도", "경북": r"경북|경상북도", "경남": r"경남|경상남도", "제주": r"제주",
}
INTENTS = [  # 앞에 있는 것이 우선
    ("forecast", r"앞으로|향후|다음에?|예측|가능성|전망|될까|할까|퍼질"),
    ("first", r"처음|최초|언제부터|먼저|시작|기원"),
    ("flow", r"퍼졌|퍼져|확산|흐름|따라|이어|다른 의회|어디로|경로|전파|참고|벤치마킹"),
    ("reasons", r"왜|이유|목적|배경|취지"),
    ("debate", r"쟁점|논란|우려|문제점|찬반|논쟁|비판"),
    ("status", r"몇 곳|몇 개|어디어디|어느 의회|가결|통과|제정|현황|조례"),
    ("said", r"뭐라고|어떻게 말|발언|언급|이야기|논의 내용"),
]
NLI_TAU = 0.5


@dataclass
class Evidence:
    n: int
    text: str                 # 근거 문장(템플릿 사실이면 사실 문장, 원문이면 원문 구간)
    kind: str                 # "fact"(카드에서 계산한 사실) | "quote"(회의록 원문)
    src: dict = field(default_factory=dict)   # council, date, doc


@dataclass
class Answer:
    question: str
    issue_id: str | None
    issue: str | None
    intent: str | None
    council: str | None
    sentences: list            # [{"text", "cites": [n], "checks": {...}, "ok": bool}]
    evidence: list             # [Evidence]
    mode: str                  # template | llm | llm→template | abstain
    note: str = ""

    def to_dict(self):
        d = self.__dict__.copy()
        d["evidence"] = [e.__dict__ for e in self.evidence]
        return d


class IssueQA:
    def __init__(self, encoder=None, nli=None, reranker=None, llm=None):
        self.cards = {}
        for f in sorted(CARDS.glob("[IP][0-9]*.json")):
            c = json.load(open(f, encoding="utf-8"))
            self.cards[c["issue_id"]] = c
        iss = pd.read_parquet(P / "issues.parquet", columns=["issue_id", "aliases", "query", "title"])
        self.iss = iss[iss.issue_id.isin(self.cards)].reset_index(drop=True)
        from src import issues as _issues
        self.alias_rx = {r.issue_id: [(a, _issues.alias_regex(a)) for a in r.aliases] for r in self.iss.itertuples()}
        self.encoder, self.nli, self.reranker, self.llm = encoder, nli, reranker, llm
        self._qvec = None
        self._ev = None

    # ------------------------------------------------------------ 1. 이해
    def resolve_issue(self, q: str):
        qn = q.replace(" ", "")
        best = None
        for iid, al in self.alias_rx.items():
            for a, rx in al:
                if re.search(rx, q) or a in qn:
                    if best is None or len(a) > best[1]:
                        best = (iid, len(a), "별칭 일치")
        if best:
            return best[0], best[2]
        if self.encoder is None:
            return None, "이슈 이름을 찾지 못했다"
        if self._qvec is None:
            self._qvec = self.encoder.encode(list(self.iss["query"]), normalize_embeddings=True, convert_to_numpy=True)
        v = self.encoder.encode([q], normalize_embeddings=True, convert_to_numpy=True)[0]
        s = self._qvec @ v
        j = int(np.argmax(s))
        if s[j] >= 0.55:
            return self.iss.issue_id[j], f"의미 유사도 {s[j]:.2f}"
        return None, f"가장 가까운 이슈 '{self.iss.title[j]}'(유사도 {s[j]:.2f})도 기준(0.55)에 못 미친다"

    @staticmethod
    def intent_of(q: str) -> str:
        for name, rx in INTENTS:
            if re.search(rx, q):
                return name
        return "summary"

    @staticmethod
    def council_of(q: str):
        for c, rx in COUNCIL_WORDS.items():
            if re.search(rx, q):
                return c
        return None

    # ------------------------------------------------------------ 2. 근거
    def _events(self):
        if self._ev is None:
            ev = pd.read_parquet(P / "events.parquet", columns=["issue_id", "pid", "council_short", "date", "mints_nm", "role",
                                                               "text", "rel", "core"])
            self._ev = ev[ev.core | (ev.rel >= 0.5)]
        return self._ev

    def gather(self, c: dict, intent: str, council: str | None, q: str) -> list[Evidence]:
        ev: list[Evidence] = []

        def add(text, kind="fact", src=None):
            ev.append(Evidence(len(ev) + 1, text, kind, src or {}))
            return ev[-1].n

        def quote(ci):
            if ci:
                add(ci["quote"].strip("…"), "quote", {k: ci.get(k) for k in ("council", "date", "doc", "role")})

        st = {s["council"]: s for s in c["status"]}
        title = c["title"]
        if intent in ("first", "summary"):
            f = c.get("first_confirmed")
            if f:
                add(f"{title} 이슈를 분명히 다룬 가장 이른 회의록은 {f['council']}의 {f['confirmed_date']} {f['confirmed']['doc']}이다.")
                quote(f["confirmed"])
            if c.get("left_censored"):
                add(f"2024년 1~3월에 이미 {c['n_early']}개 의회가 언급해, 이 이슈의 기원은 데이터 시작(2024-01) 이전일 수 있다.")
            bills = sorted([s for s in c["status"] if s.get("bill_date")], key=lambda s: s["bill_date"])
            if bills:
                add(f"조례 안건을 가장 먼저 상정한 의회는 {bills[0]['council']}이다(상정일 {bills[0]['bill_date']}).")
        if intent in ("flow", "summary", "status"):
            bills = sorted([s for s in c["status"] if s.get("bill_date")], key=lambda s: s["bill_date"])
            passed = [s["council"] for s in c["status"] if s["stage"] == "본회의 가결"]
            add(f"{title} 이슈는 17개 의회 중 {c['n_councils']}곳에서 논의되었고, {len(bills)}곳이 조례 안건을 상정했으며, "
                f"본회의 가결이 확인된 곳은 {len(passed)}곳이다.")
            if bills:
                add("조례 상정 순서는 " + ", ".join(f"{s['council']}({s['bill_date'][:7]})" for s in bills[:17]) + "이다.")
            add(f"이슈 유형은 '{c['type']}'이다. 근거: {c['type_why']}.")
            if intent == "flow":
                for r in c.get("ref_examples", [])[:3]:
                    quote(r)
                if c.get("top_law") and c["type"] == "법 대응형":
                    quote(c["top_law"].get("example"))
        if intent in ("forecast", "summary"):
            fc = c.get("forecast")
            if fc and fc["councils"]:
                top = [r for r in fc["councils"] if r["grade"] == "상"]
                add(f"2025-12-31 기준 다음 6개월 안에 새로 조례를 상정할 것으로 예상되는 의회 수는 {fc['expected_new']}곳"
                    f"(80% 구간 {fc['interval80'][0]}~{fc['interval80'][1]}곳)이고, 확산 단계는 '{fc['stage']}'이다.")
                if top:
                    g = fc["grades"]["상"]
                    add("예측 등급 '상'인 의회는 " + ", ".join(f"{r['council_short']}({r['p'] * 100:.0f}%)" for r in top)
                        + f"이다. 백테스트에서 '상' 등급이 실제로 6개월 안에 상정한 비율은 {g['rate'] * 100:.1f}%였다.")
            elif fc:
                add(f"{title} 이슈는 17개 의회가 모두 안건을 내 포화 상태라 새로 상정할 의회가 남지 않았다.")
            elif c.get("outlook"):
                o = c["outlook"]
                add(f"{title}는 조례 안건이 없어 예측 모형의 대상이 아니다. 논의 지표로 본 전망은 '{o['stage']}'이며, "
                    f"2025 하반기에 새로 논의를 시작한 의회는 {o['new_2025h2']}곳이다.")
        if intent == "reasons":
            for r in c.get("reasons", [])[:4]:
                quote(r)
        if intent == "debate" and c.get("clusters"):
            for k in c["clusters"]["clusters"][:3]:
                add(f"쟁점 묶음({', '.join(k['keywords'][:4])})은 {k['n_councils']}개 의회의 문장 {k['n_sent']}개로 이루어진다.")
                if k["reps"]:
                    quote(k["reps"][0])
        if intent == "status" and council:
            s = st.get(council)
            if s:
                txt = f"{council}의 단계는 '{s['stage']}'이다."
                if s.get("bill_date"):
                    txt += f" {s['bill_date']}에 「{s.get('bill_title', '')}」을 상정했다."
                if s.get("plenary_pass"):
                    txt += f" 본회의 가결일은 {s['plenary_pass']}이다."
                add(txt)
        if intent == "said" or (council and intent in ("first", "summary")):
            for p in self.search_passages(c["issue_id"], q, council, k=3):
                add(p["text"], "quote", {k: p[k] for k in ("council", "date", "doc", "role")})
        if council and intent == "first":
            s = st.get(council)
            if s and s.get("first_date"):
                add(f"{council}에서 이 이슈가 처음 관측된 날은 {s['first_date']}이고, 분명히 다룬 첫 회의는 {s.get('confirmed_date') or '확인되지 않았다'}.")
        return ev

    def search_passages(self, issue_id, q, council=None, k=3):
        ev = self._events()
        g = ev[ev.issue_id == issue_id]
        if council:
            g = g[g.council_short == council]
        if g.empty:
            return []
        g = g.nlargest(60, "rel")
        if self.reranker is not None:
            s = self.reranker.predict([(q, t[:600]) for t in g.text], show_progress_bar=False)
            g = g.assign(s=s).nlargest(k, "s")
        else:
            g = g.head(k)
        out = []
        for r in g.itertuples():
            sent = best_sentence(r.text, q)
            out.append({"text": sent, "council": r.council_short, "date": str(r.date.date()), "doc": r.mints_nm, "role": r.role})
        return out

    # ------------------------------------------------------------ 3·4. 답 만들기와 검증
    def template_answer(self, ev: list[Evidence]) -> list[dict]:
        out = []
        for e in ev:
            if e.kind == "fact":
                out.append({"text": e.text, "cites": [e.n] + [x.n for x in ev if x.kind == "quote" and x.n == e.n + 1][:1],
                            "checks": {"template": True}, "ok": True})
        return out

    def llm_answer(self, q, ev: list[Evidence]) -> list[dict]:
        ctx = "\n".join(f"[{e.n}] " + (f"({e.src.get('council')} {e.src.get('date')} 회의록 원문) " if e.kind == "quote" else "")
                        + e.text for e in ev)
        msgs = [{"role": "system", "content": LLM_SYSTEM},
                {"role": "user", "content": f"근거:\n{ctx}\n\n질문: {q}\n\n답(문장마다 근거 번호):"}]
        out = self.llm.create_chat_completion(messages=msgs, temperature=0.0, max_tokens=320)
        text = out["choices"][0]["message"]["content"].strip()
        return [{"text": s, "cites": [int(x) for x in re.findall(r"\[(\d+)\]", s)], "checks": {}, "ok": None}
                for s in split_sentences(text)]

    def verify(self, sents: list[dict], ev: list[Evidence]) -> list[dict]:
        byn = {e.n: e for e in ev}
        for s in sents:
            body = re.sub(r"\s*\[\d+\]", "", s["text"]).strip()
            cited = [byn[n] for n in s["cites"] if n in byn]
            ck = {"has_citation": bool(cited)}
            ctext = " ".join(e.text + " " + " ".join(str(v) for v in e.src.values() if v) for e in cited)
            ents = entities(body)
            missing = [x for x in ents if norm(x) not in norm(ctext)]
            ck["entities_supported"] = not missing
            if missing:
                ck["missing"] = missing
            if cited and self.nli is not None:
                prem = [p for e in cited for p in split_sentences(e.text)] or [ctext]
                probs = self.nli.nli_probs(prem, [body] * len(prem))[:, 0]
                ck["nli_entail"] = round(float(probs.max()), 3)
            ok = ck["has_citation"] and ck["entities_supported"] and ck.get("nli_entail", 1.0) >= NLI_TAU
            s.update(text=body, checks=ck, ok=bool(ok))
        return sents

    def ask(self, q: str, use_llm: bool = False) -> Answer:
        iid, how = self.resolve_issue(q)
        intent, council = self.intent_of(q), self.council_of(q)
        if iid is None:
            return Answer(q, None, None, intent, council, [], [], "abstain", f"답하지 않음: {how}")
        c = self.cards[iid]
        ev = self.gather(c, intent, council, q)
        if not ev:
            return Answer(q, iid, c["title"], intent, council, [], [], "abstain", "답하지 않음: 이 질문에 맞는 근거가 카드에 없다")
        tmpl = self.template_answer(ev)
        if not use_llm or self.llm is None:
            return Answer(q, iid, c["title"], intent, council, tmpl, ev, "template", f"이슈 찾기: {how}")
        gen = self.verify(self.llm_answer(q, ev), ev)
        kept = [s for s in gen if s["ok"]]
        if not kept:
            return Answer(q, iid, c["title"], intent, council, tmpl, ev, "llm→template",
                          f"생성 문장 {len(gen)}개가 모두 검증에 실패해 템플릿 답으로 대체")
        return Answer(q, iid, c["title"], intent, council, kept, ev, "llm",
                      f"생성 문장 {len(gen)}개 중 {len(kept)}개 통과(실패 문장은 버림)" + (f"; 버린 문장: {[s['text'] for s in gen if not s['ok']]}" if len(kept) < len(gen) else ""))


LLM_SYSTEM = ("너는 지방의회 회의록 분석 결과를 설명하는 도우미다. 반드시 주어진 근거만 사용한다. "
              "모든 문장 끝에 그 문장을 뒷받침하는 근거 번호를 [1]처럼 붙인다. 근거에 없는 날짜, 숫자, 의회 이름, 인과 관계를 "
              "만들지 않는다. 시간 순서를 영향 관계로 바꿔 말하지 않는다('A가 먼저 했으니 B가 따라했다' 금지). "
              "근거로 답할 수 없으면 '근거가 부족해 답할 수 없다'고 쓴다. 3문장 이내, 한국어 평서문으로 답한다.")


def split_sentences(t: str) -> list[str]:
    parts = re.split(r"(?<=[.?!다])\s+(?=\S)", t.strip())
    out = []
    for p in parts:   # 인용 번호가 다음 문장 앞에 붙은 경우를 앞 문장으로 돌린다
        m = re.match(r"^((?:\[\d+\]\s*)+)(.*)$", p)
        if m and out:
            out[-1] += " " + m.group(1).strip()
            p = m.group(2)
        if p.strip():
            out.append(p.strip())
    return out


def best_sentence(text: str, q: str, width: int = 220) -> str:
    """원문 문단에서 질문과 낱말이 가장 많이 겹치는 문장(앞뒤 한 문장 포함)을 고른다."""
    ss = [s.strip() for s in re.split(r"(?<=[.?!])\s+|\n", text) if s.strip()]
    if not ss:
        return text[:width]
    qw = set(re.findall(r"[가-힣A-Za-z]{2,}", q))
    j = max(range(len(ss)), key=lambda i: len(qw & set(re.findall(r"[가-힣A-Za-z]{2,}", ss[i]))))
    s = " ".join(ss[max(0, j - 1): j + 2])
    return s[:width] + ("…" if len(s) > width else "")


def entities(s: str) -> list[str]:
    """검증할 개체: 날짜, 숫자(퍼센트 포함), 의회 이름."""
    out = re.findall(r"\d{4}-\d{2}(?:-\d{2})?|\d{4}년\s?\d{1,2}월(?:\s?\d{1,2}일)?|\d+(?:\.\d+)?%?", s)
    for c, rx in COUNCIL_WORDS.items():
        if re.search(rx, s):
            out.append(c)
    return [x for x in out if x not in ("1", "2", "3")]


def norm(s: str) -> str:
    s = re.sub(r"(\d{4})년\s?(\d{1,2})월(?:\s?(\d{1,2})일)?", lambda m: f"{m.group(1)}-{int(m.group(2)):02d}" + (f"-{int(m.group(3)):02d}" if m.group(3) else ""), s)
    for c, rx in COUNCIL_WORDS.items():
        s = re.sub(rx, c, s)
    return s.replace(" ", "")


def load_llm(n_ctx=4096):
    """로컬 Qwen2.5-7B-Instruct(Q4_K_M GGUF). llama.cpp가 CUDA DLL을 PATH로만 찾으므로 torch/lib을 앞에 붙인다."""
    import os

    import torch
    os.environ["PATH"] = str(Path(torch.__file__).parent / "lib") + os.pathsep + os.environ["PATH"]
    from huggingface_hub import hf_hub_download
    from llama_cpp import Llama
    path = hf_hub_download("Qwen/Qwen2.5-7B-Instruct-GGUF", "qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf")
    hf_hub_download("Qwen/Qwen2.5-7B-Instruct-GGUF", "qwen2.5-7b-instruct-q4_k_m-00002-of-00002.gguf")
    return Llama(model_path=path, n_gpu_layers=-1, n_ctx=n_ctx, verbose=False, seed=0)
