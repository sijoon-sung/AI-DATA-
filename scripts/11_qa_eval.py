"""11단계 실험: 근거 기반 질의응답의 정확도, 인용 품질, 답하지 않기.

질문 세트(자동 + 수작업)
  - 카드에서 만든 질문: 이슈마다 최초 관측, 상정 의회 수, 6개월 신규 예상, 특정 의회의 단계. 정답은 카드의 값이다.
    (이 실험은 '질의응답 층이 카드의 사실을 틀리지 않고 옮기는가'를 잰다. 카드 자체의 정확도는 정답셋으로 따로 잰다.)
  - 바꿔 말한 질문(PARAPHRASE): 별칭을 쓰지 않고 묻는 질문. 이슈 찾기(bge-m3 유사도)를 시험한다.
  - 카드 범위 밖 질문(OUT_OF_SCOPE): 답하지 않아야 맞다.
비교: template(템플릿 답) / llm-raw(Qwen 생성 그대로) / llm-verified(문장 검증 후, 실패 시 템플릿으로)
지표
  - 이슈 찾기 정확도, 범위 밖 질문에서 답하지 않은 비율
  - 정답 포함률: 정답 값(의회 이름, 날짜, 수)이 최종 답 문장에 들어 있는 비율
  - ALCE 방식 인용 지표(Gao et al. 2023, "Enabling Large Language Models to Generate Text with Citations"):
      인용 재현율 = 인용한 근거가 문장을 함의하는 문장의 비율
      인용 정밀도 = 인용 하나하나가 (혼자 함의하거나) 빼면 함의가 깨지는 경우의 비율
    ALCE는 인용 문단을 이어 붙인 전제로 TRUE(T5-11B)를 쓰지만, 여기서는 KLUE-NLI KoELECTRA를 쓰고 전제를 문장 단위로
    나눠 최댓값을 쓴다(긴 전제에서 이 판정기가 거의 '중립'만 내는 것을 10/11에 확인했다).
  - 근거 없는 문장 비율(검증 전/후)
출력: results/qa_eval.json
실행: python scripts/11_qa_eval.py [--llm] [--limit N]
"""
import argparse
import json
import random
import re
import sys
import time
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.qa import IssueQA, entities, norm, split_sentences  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--llm", action="store_true")
ap.add_argument("--limit", type=int, default=0)
args = ap.parse_args()
t0 = time.time()

# 별칭 없이 바꿔 말한 질문(이슈 ID, 질문). 회의록 원문이 아니라 직접 쓴 문장이다.
PARAPHRASE = [
    ("I0029", "전기차 충전구역 화재를 막는 조례는 어디서 처음 나왔어?"),
    ("I2526", "역세권 고밀 복합 개발을 지원하는 조례는 몇 곳이 만들었나?"),
    ("I0120", "지역에서 전기를 생산해 쓰는 분산형 에너지 지원 조례는 앞으로 어디가 할까?"),
    ("I0165", "AI 산업을 키우는 조례는 어디서 처음 논의됐나?"),
    ("I0684", "고등학생이 과목을 골라 듣는 학점제 지원 조례는 몇 곳이 상정했어?"),
    ("I0237", "딥페이크 같은 디지털 성범죄 예방 교육 조례는 어디서 처음?"),
    ("I1066", "묻지마 범죄 피해자 지원 조례는 어디로 퍼졌나?"),
    ("I0358", "자율주행차 시범지구 조례는 앞으로 어디가 만들 것 같아?"),
    ("I0251", "UAM 산업 육성 조례는 몇 곳이 만들었어?"),
    ("I0484", "식품 기술 산업 육성 조례를 왜 만들었대?"),
    ("I0802", "펫 산업을 지원하는 조례는 어디서 처음 상정했나?"),
    ("I0263", "폐현수막을 재활용하는 조례는 어디로 퍼졌어?"),
    ("I1224", "학생 헌혈 교육을 늘리는 조례는 몇 곳이 만들었나?"),
    ("I0910", "의원을 돕는 정책지원 인력 운영 조례는 어디서 처음?"),
    ("I0340", "양자 기술 산업 육성 조례는 앞으로 어디가 할까?"),
]
OUT_OF_SCOPE = [
    "반려동물 보험 의무화 조례는 어디서 처음 나왔어?", "공무원 주 4일제 조례는 몇 곳이 만들었어?",
    "지하철 무료 와이파이 조례는 어디로 퍼졌나?", "드론 택배 지원 조례는 앞으로 어디가 할까?",
    "해수욕장 야간 개장 조례를 왜 만들었대?", "외국인 계절근로자 숙소 조례는 어디서 처음?",
    "길고양이 급식소 조례는 몇 곳이 상정했나?", "1인 가구 고독사 예방 앱 조례는 어디로 퍼졌어?",
    "스마트 가로등 설치 조례는 앞으로 어디가 만들까?", "청소년 게임 셧다운 조례는 어디서 처음 논의됐어?",
]


def card_questions(qa: IssueQA):
    out = []
    for iid, c in qa.cards.items():
        t = c["title"]
        f = c.get("first_confirmed")
        if f:
            out.append(dict(issue=iid, type="first", q=f"{t} 이슈는 어느 의회에서 처음 논의됐나?", gold=[f["council"], f["confirmed_date"]]))
        bills = [s for s in c["status"] if s.get("bill_date")]
        if bills:
            out.append(dict(issue=iid, type="flow", q=f"{t} 조례 안건은 몇 개 의회가 상정했나?", gold=[f"{len(bills)}곳"]))
        fc = c.get("forecast")
        if fc and fc["councils"]:
            out.append(dict(issue=iid, type="forecast", q=f"{t} 조례를 앞으로 6개월 안에 새로 상정할 의회는 몇 곳으로 예상되나?",
                            gold=[f"{fc['expected_new']}곳"]))
        passed = [s for s in c["status"] if s["stage"] == "본회의 가결"]
        if passed:
            s = random.Random(iid).choice(passed)
            out.append(dict(issue=iid, type="status", q=f"{s['council']}는 {t} 조례를 가결했나?", gold=["본회의 가결"]))
    return out


def contains(ans: str, gold: list[str]) -> bool:
    a = norm(ans)
    return all(norm(g) in a for g in gold)


def alce(sents, ev, nli):
    """ALCE 방식 인용 재현율·정밀도(문장 단위 전제의 최댓값으로 함의 판정)."""
    byn = {e.n: e for e in ev}

    def ent(prem_evs, hyp):
        prem = [p for e in prem_evs for p in split_sentences(e.text)]
        return bool(prem) and float(nli.nli_probs(prem, [hyp] * len(prem))[:, 0].max()) >= 0.5

    rec, prec_hits, prec_n = [], 0, 0
    for s in sents:
        body = re.sub(r"\s*\[\d+\]", "", s["text"]).strip()
        cited = [byn[n] for n in s["cites"] if n in byn]
        if s.get("checks", {}).get("template"):   # 템플릿 문장은 근거 문장 그 자체다
            rec.append(1); prec_hits += len(cited); prec_n += len(cited)
            continue
        r = ent(cited, body) if cited else False
        rec.append(int(r))
        for e in cited:
            prec_n += 1
            alone = ent([e], body)
            rest = [x for x in cited if x is not e]
            if alone or (r and not (rest and ent(rest, body))):
                prec_hits += 1
    return (sum(rec) / len(rec) if rec else None), (prec_hits / prec_n if prec_n else None)


def main():
    import torch
    from sentence_transformers import CrossEncoder, SentenceTransformer

    from src import nli
    from src.qa import load_llm
    llm = load_llm() if args.llm else None
    dev = "cpu" if (args.llm or not torch.cuda.is_available()) else "cuda"
    kw = {"torch_dtype": torch.float16} if dev == "cuda" else {}
    qa = IssueQA(encoder=SentenceTransformer("BAAI/bge-m3", device=dev, model_kwargs=kw), nli=nli,
                 reranker=CrossEncoder("BAAI/bge-reranker-v2-m3", device=dev, max_length=384, model_kwargs=kw), llm=llm)
    items = card_questions(qa)
    items += [dict(issue=i, type="paraphrase", q=q, gold=None) for i, q in PARAPHRASE]
    items += [dict(issue=None, type="out_of_scope", q=q, gold=None) for q in OUT_OF_SCOPE]
    if args.limit:
        items = random.Random(0).sample(items, min(args.limit, len(items)))
    modes = ["template"] + (["llm"] if llm else [])
    rows = []
    for k, it in enumerate(items, 1):
        for mode in modes:
            a = qa.ask(it["q"], use_llm=(mode == "llm"))
            row = dict(it, mode=mode, resolved=a.issue_id, answer_mode=a.mode, note=a.note[:200],
                       final=" ".join(s["text"] for s in a.sentences))
            if mode == "llm" and a.mode != "abstain":
                raw = qa.verify(qa.llm_answer(it["q"], a.evidence), a.evidence)   # 검증 전 생성 문장(같은 근거, 온도 0)
                row["raw_sentences"] = len(raw)
                row["raw_unsupported"] = sum(1 for s in raw if not s["ok"])
                row["raw_text"] = " ".join(s["text"] for s in raw)
                row["raw_correct"] = contains(row["raw_text"], it["gold"]) if it["gold"] else None
                row["raw_cite_recall"], row["raw_cite_precision"] = alce(raw, a.evidence, nli)
            if a.sentences and a.mode != "abstain":
                row["cite_recall"], row["cite_precision"] = alce(a.sentences, a.evidence, nli)
            row["correct"] = contains(row["final"], it["gold"]) if it["gold"] else None
            rows.append(row)
        if k % 20 == 0:
            print(f"[{time.time() - t0:5.0f}초] {k}/{len(items)}", flush=True)

    import pandas as pd
    df = pd.DataFrame(rows)
    summ = {}
    for mode, g in df.groupby("mode"):
        ans = g[g.type != "out_of_scope"]
        oos = g[g.type == "out_of_scope"]
        para = g[g.type == "paraphrase"]
        s = {"n_questions": int(len(g)),
             "issue_resolution_acc": round(float((ans.resolved == ans.issue).mean()), 3),
             "paraphrase_resolution_acc": round(float((para.resolved == para.issue).mean()), 3) if len(para) else None,
             "out_of_scope_abstain": round(float((oos.answer_mode == "abstain").mean()), 3) if len(oos) else None,
             "answer_correct": round(float(ans.correct.dropna().astype(float).mean()), 3),
             "cite_recall": round(float(g.cite_recall.dropna().mean()), 3) if "cite_recall" in g else None,
             "cite_precision": round(float(g.cite_precision.dropna().mean()), 3) if "cite_precision" in g else None,
             "by_type_correct": {t: round(float(x.correct.dropna().astype(float).mean()), 3)
                                 for t, x in ans.groupby("type") if x.correct.notna().any()}}
        if mode == "llm":
            s.update(raw_unsupported_sentence_rate=round(float(g.raw_unsupported.sum() / max(g.raw_sentences.sum(), 1)), 3),
                     raw_answer_correct=round(float(g.raw_correct.dropna().astype(float).mean()), 3),
                     raw_cite_recall=round(float(g.raw_cite_recall.dropna().mean()), 3),
                     raw_cite_precision=round(float(g.raw_cite_precision.dropna().mean()), 3),
                     fallback_to_template=round(float((g.answer_mode == "llm→template").mean()), 3))
        summ[mode] = s
        print(mode, json.dumps(s, ensure_ascii=False), flush=True)
    (ROOT / "results").mkdir(exist_ok=True)
    json.dump({"summary": summ, "rows": rows}, open(ROOT / "results" / "qa_eval.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1, default=str)
    print(f"완료 ({time.time() - t0:.0f}초)")


if __name__ == "__main__":
    main()
