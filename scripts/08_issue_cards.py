"""8단계: 핵심 이슈 목록 → 사건표 → 관련 판정 → 예측 → 이슈 카드·목차·대회 결과표.

출력
  data/processed/issues.parquet   선정한 이슈와 별칭, 점수
  data/processed/events.parquet   이슈별 후보 문단(원문 포함), 관련 점수, 핵심 별칭 여부
  data/processed/events_aliases.json  사건표를 만들 때의 별칭 목록과 별칭별 문단 수
  results/issue_cards/<이슈ID>.html·.json, results/issue_cards/index.html
  results/issue_table.csv         대회 요구 항목(이슈 키워드, 최초 관측, 흐름, 향후 예측, 근거)
  results/forecast_backtest.json  예측 백테스트 지표와 등급별 실측 빈도
results/ 와 data/processed/ 는 회의록 원문을 담으므로 공개 저장소에 올리지 않는다.
LLM은 쓰지 않는다(규칙 + bge-m3 + bge-reranker).

실행: python scripts/08_issue_cards.py [--n-inst 30] [--n-proper 10] [--reuse-events]
"""
import argparse
import json
import sys
import time
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import pyarrow.dataset as ds  # noqa: E402
from src import cards, events, forecast, issues, retrieve  # noqa: E402
from src.render_card import competition_row, render, render_index  # noqa: E402

P = ROOT / "data" / "processed"
OUT = ROOT / "results" / "issue_cards"
ap = argparse.ArgumentParser()
ap.add_argument("--n-inst", type=int, default=30)
ap.add_argument("--n-proper", type=int, default=10)
ap.add_argument("--reuse-events", action="store_true", help="저장된 사건표와 관련 점수를 다시 쓴다(카드 규칙만 바꿨을 때)")
ap.add_argument("--no-semantic", action="store_true", help="하이브리드 검색으로 별칭 없는 언급을 찾는 단계를 건너뛴다")
args = ap.parse_args()
t0 = time.time()


def log(msg):
    print(f"[{time.time() - t0:6.0f}초] {msg}", flush=True)


# ---------------------------------------------------------------- 1. 이슈 목록
docs = pd.read_parquet(P / "docs.parquet", columns=["doc_id", "council_short", "date", "mints_nm", "keep"])
docs = docs[docs.keep].drop(columns="keep")
docs["plenary"] = docs.mints_nm.str.contains("본회의")
ag = pd.read_parquet(P / "agenda.parquet", columns=["doc_id", "no", "title", "kind"]).merge(docs, on="doc_id")
bills_all = issues.bill_rows(ag)
pol, inst, model = issues.instruments(bills_all)
scored = issues.score_instruments(inst)
sel = scored[(scored.n_councils >= 3) & (scored.aliases.map(len) > 0)].head(args.n_inst)
log(f"안건 {len(bills_all):,}행 → 정책 수단 {len(inst):,}개, 선정 {len(sel)}개: "
    + ", ".join(f"{r.name}({r.n_enact}/{r.n_councils})" for r in sel.itertuples()))

title_text = "".join(bills_all.name.str.replace(" ", "", regex=False))
prop = issues.proper_noun_candidates(P / "passages.parquet", docs, title_text)
inst_alias = {a for al in sel.aliases for a in al}
prop = prop[~prop.name.map(lambda w: any(a in w or w in a for a in inst_alias))]
# 같은 정책의 다른 표기('AI디지털교과서'와 '디지털교과서', '청년문화패스'와 '청년문화예술패스')는 하나로 묶는다:
# 접미어가 같고, 앞의 영문과 접미어를 뗀 앞말이 비어 있지 않으며 한쪽이 다른 쪽에 들어 있으면 합친다.
# ('K패스'와 '경기패스'처럼 앞말이 다르면 다른 정책이다.)
import re  # noqa: E402


def split_stem(w):
    suf = re.search(issues.PROPER_SUFFIX + "$", w)
    return re.sub(r"^[A-Za-z]+", "", w[: suf.start()] if suf else w), (suf.group(0) if suf else "")


def same_policy(a, b):
    (sa, fa), (sb, fb) = split_stem(a), split_stem(b)
    if fa != fb:
        return False
    if sa and sb:
        return sa in sb or sb in sa
    ra, rb = a[: len(a) - len(fa)], b[: len(b) - len(fb)]   # 'AI교과서'와 'AI디지털교과서': 영문 앞말끼리 비교
    return len(min(ra, rb, key=len)) >= 2 and (ra in rb or rb in ra)


groups = []
for r in prop.itertuples():
    g = next((g for g in groups if any(same_policy(r.name, x) for x in g["aliases"])), None)
    if g:
        g["aliases"].append(r.name)
    elif len(groups) < args.n_proper:
        groups.append({"name": r.name, "aliases": [r.name], "score": r.score})
log(f"발언 전용 후보 {len(prop):,}개, 선정 {len(groups)}개: {', '.join(g['name'] + ('(' + '·'.join(g['aliases'][1:]) + ')' if len(g['aliases']) > 1 else '') for g in groups)}")

specs = []
for r in sel.itertuples():
    specs.append(dict(issue_id=f"I{r.inst_id:04d}", kind="inst", inst_id=r.inst_id, name=r.name, title=r.name, theme=r.theme,
                      aliases=r.aliases, regex="|".join(issues.alias_regex(a) for a in r.aliases),
                      query=f"{r.name} ({', '.join(r.names[:3])})", stop=set(issues.core_tokens(" ".join(r.aliases))),
                      base_score=float(r.score)))
for k, g in enumerate(groups, 1):
    specs.append(dict(issue_id=f"P{k:02d}", kind="proper", inst_id=None, name=g["name"], title=g["name"], theme="",
                      aliases=g["aliases"], regex="|".join(issues.alias_regex(a) for a in g["aliases"]),
                      query=g["name"], stop=set(g["aliases"]), base_score=1.0))

# ---------------------------------------------------------------- 2. 사건표와 관련 판정
pat = {s["issue_id"]: [(a, issues.alias_regex(a)) for a in s["aliases"]] for s in specs}
side = P / "events_aliases.json"   # 사건표를 만들 때의 별칭 목록, 남긴 별칭, 별칭별 문단 수
if args.reuse_events and (P / "events.parquet").exists() and side.exists():
    meta = json.load(open(side, encoding="utf-8"))
    if meta["aliases"] != {k: [a for a, _ in v] for k, v in pat.items()}:
        sys.exit("저장된 사건표의 이슈·별칭이 지금 목록과 다르다. --reuse-events 없이 다시 실행해야 한다.")
    ev, kept, counts = pd.read_parquet(P / "events.parquet").drop(columns="core", errors="ignore"), meta["kept"], meta["counts"]
    if args.no_semantic and "source" in ev:
        ev = ev[ev.source != "semantic"].reset_index(drop=True)
    log(f"사건표 재사용: 문단 {len(ev):,}개")
else:
    ev, kept, counts = events.scan(P / "passages.parquet", pat, docs)
    log(f"사건표 후보 문단 {len(ev):,}개")
    # 후보 문단 전부에 관련 점수를 매긴다(GPU에서 3만 쌍에 약 3분)
    ev["rel"] = events.relevance(ev, {s["issue_id"]: s["query"] for s in specs}).values
    log(f"관련 점수 {len(ev):,}개 계산 (0.5 이상 {(ev.rel >= 0.5).mean():.2f})")
    json.dump({"aliases": {k: [a for a, _ in v] for k, v in pat.items()}, "kept": kept, "counts": counts},
              open(side, "w", encoding="utf-8"), ensure_ascii=False)

# 별칭 구분: 대표 별칭(첫 별칭)과, 관련 비율이 대표 별칭의 절반 이상인 별칭은 핵심 별칭이다. 핵심 별칭으로 걸린 문단은
# 관련 점수와 상관없이 쓴다(재순위 점수는 'K패스가 5월부터 진행되고…' 같은 짧은 대화체 언급에도 낮게 나온다).
# 나머지는 넓은 별칭('국가유산', '복합개발', '피해학생' 등)이며, 그 별칭으로만 걸린 문단은 관련 점수 0.5 이상일 때만 쓴다.
ev["core"] = False
for s in specs:
    m = (ev.issue_id == s["issue_id"]).to_numpy()
    g = ev[m]
    bits = g.alias_bits.to_numpy(dtype="int64")
    keep = kept.get(s["issue_id"], s["aliases"])
    stats = []
    for j, a in enumerate(s["aliases"]):
        hit = ((bits >> j) & 1).astype(bool)
        st = dict(alias=a, n=int(counts.get(s["issue_id"], {}).get(a, hit.sum())), prec=None, status="")
        if a in keep:
            st["prec"] = round(float((g.rel[hit] >= cards.REL_TAU).mean()), 3) if hit.any() else None
        else:
            st["status"] = "너무 넓게 걸려 제외(대표 별칭의 4배 초과)"
        stats.append(st)
    p0 = stats[0]["prec"] or 0.0
    core_mask = 0
    for j, st in enumerate(stats):
        if st["status"]:
            continue
        if j == 0 or (st["prec"] is not None and st["prec"] >= 0.5 * p0):
            st["status"], core_mask = "핵심 별칭: 걸린 문단 모두 사용", core_mask | (1 << j)
        else:
            st["status"] = "넓은 별칭: 관련 점수 0.5 이상 문단만 사용"
    ev.loc[m, "core"] = (bits & core_mask) > 0
    s["alias_stats"] = stats
    s["aliases"] = keep
    s["regex"] = "|".join(issues.alias_regex(a) for a in keep)
    log(f'  {s["issue_id"]} {s["title"]}: ' + ", ".join(
        f'{x["alias"]} {x["n"]:,}' + (" (제외)" if x["prec"] is None and x["status"].startswith("너무") else
                                      f' ({(x["prec"] or 0):.0%}{"" if x["status"].startswith("핵심") else ", 넓음"})')
        for x in stats))
if "source" not in ev:
    ev["source"] = "alias"
ev["source"] = ev.source.fillna("alias")

# ---------------------------------------------------------------- 2-2. 하이브리드 검색으로 별칭 없는 언급 찾기
# 별칭 정규식은 바꿔 쓴 표현('전기차 충전구역 화재 대책')을 놓친다. 의회별 BM25 + bge-m3 검색을 RRF로 합쳐 찾고
# (src/retrieve.py), 교차 인코더 점수 0.5 이상만 근거로 쓴다. 발언 전용 고유명사 이슈는 이름 자체가 이슈이므로 하지 않는다.
if not args.no_semantic and not (ev.source == "semantic").any() and retrieve.index_ready():
    import torch
    from sentence_transformers import SentenceTransformer
    enc = SentenceTransformer("BAAI/bge-m3", device="cuda" if torch.cuda.is_available() else "cpu",
                              model_kwargs={"torch_dtype": torch.float16} if torch.cuda.is_available() else {})
    queries = {}
    for s in specs:
        if s["kind"] != "inst":
            continue
        g = ev[(ev.issue_id == s["issue_id"]) & (ev.core | (ev.rel >= cards.REL_TAU))].nlargest(20, "rel")
        cen = enc.encode(g.text.str[:600].tolist(), normalize_embeddings=True, convert_to_numpy=True).mean(0)
        queries[s["issue_id"]] = {"text": s["query"], "tokens": retrieve.bm25_tokens([s["query"]])[0],
                                  "vecs": [cen / np.linalg.norm(cen)]}
    hits = retrieve.hybrid_search(queries, k=30, k_each=100, encoder=enc)
    del enc
    have = set(zip(ev.issue_id, ev.pid))
    new = hits[[(q, x) not in have for q, x in zip(hits.qid, hits.pid)]]
    tbl = ds.dataset(P / "passages.parquet").to_table(columns=events.COLS, filter=ds.field("pid").isin(list(new.pid.unique())))
    add = (new[["qid", "pid", "rrf"]].rename(columns={"qid": "issue_id"}).merge(tbl.to_pandas(), on="pid").merge(docs, on="doc_id")
           .assign(alias_bits=0, source="semantic", core=False))
    add["rel"] = events.relevance(add, {s["issue_id"]: s["query"] for s in specs}).values
    before = ev[ev.rel >= cards.REL_TAU].groupby(["issue_id", "council_short"]).date.min()
    ev = pd.concat([ev, add], ignore_index=True).sort_values(["issue_id", "date", "doc_id", "start"]).reset_index(drop=True)
    after = ev[ev.rel >= cards.REL_TAU].groupby(["issue_id", "council_short"]).date.min()
    cmp = pd.concat([before.rename("b"), after.rename("a")], axis=1)
    log(f"하이브리드 검색: 새 후보 {len(add):,}개 중 관련 점수 0.5 이상 {int((add.rel >= cards.REL_TAU).sum()):,}개. "
        f"확인된 첫 관측이 앞당겨진 (이슈, 의회) {int((cmp.a < cmp.b).sum())}쌍, 새로 생긴 쌍 {int(cmp.b.isna().sum())}개")
ev.to_parquet(P / "events.parquet", index=False)
use = ev.core | (ev.rel >= cards.REL_TAU)
log(f"근거 문단 {int(use.sum()):,}개 / 후보 {len(ev):,}개 (넓은 별칭으로만 걸리고 관련 점수가 낮아 뺀 문단 {int((~use).sum()):,}개)")
pd.DataFrame([{k: (list(v) if isinstance(v, set) else v) for k, v in s.items()} for s in specs]).to_parquet(P / "issues.parquet", index=False)

# ---------------------------------------------------------------- 3. 예측
fc = forecast.run(pol)
fc_meta = {"b0": fc["b0"], "grades": fc["grades"], "metrics": fc["metrics"], "coef": fc["coef"]}
(ROOT / "results").mkdir(exist_ok=True)
json.dump(fc_meta, open(ROOT / "results" / "forecast_backtest.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
log(f"예측: {fc['metrics']} / 등급 {fc['grades']}")

# ---------------------------------------------------------------- 4. 카드
tot_counts = {}
for b in pq.ParquetFile(P / "passages.parquet").iter_batches(columns=["doc_id"], batch_size=500_000):
    for k, v in pd.Series(b.column("doc_id").to_pylist()).value_counts().items():
        tot_counts[k] = tot_counts.get(k, 0) + v
totals = (docs.assign(n=docs.doc_id.map(tot_counts).fillna(0), month=docs.date.dt.to_period("M").astype(str))
          .groupby(["council_short", "month"]).n.sum().reset_index())
from kiwipiepy import Kiwi  # noqa: E402
from src import nli  # noqa: E402
kiwi = Kiwi()
OUT.mkdir(parents=True, exist_ok=True)
built = []
for s in specs:
    pas = ev[ev.issue_id == s["issue_id"]]
    if pas.empty:
        continue
    if s["kind"] == "inst":
        bills = pol[pol.inst_id == s["inst_id"]]
        fc_rows = fc["final"][fc["final"].inst_id == s["inst_id"]]
    else:
        bills = bills_all[bills_all.title.str.contains(s["regex"], regex=True)]
        fc_rows = None
    card = cards.build_card(s, pas, bills, totals, P / "docs.parquet", fc_rows, fc_meta, model, kiwi, nli)
    n_bill = sum(1 for x in card["status"] if x.get("bill_date"))
    card["rank_score"] = round(s["base_score"] + 0.5 * card["n_councils"] + (0 if s["kind"] == "inst" else n_bill), 2)
    json.dump(card, open(OUT / f'{s["issue_id"]}.json', "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    (OUT / f'{s["issue_id"]}.html').write_text(render(card), encoding="utf-8")
    built.append(card)
    log(f'카드 {s["issue_id"]} {s["title"]}: 근거 문단 {card["n_passages"]:,}/{len(pas):,}, 의회 {card["n_councils"]}, 유형 {card["type"]}')

built.sort(key=lambda c: -c["rank_score"])
(OUT / "index.html").write_text(render_index(built, fc_meta), encoding="utf-8")
pd.DataFrame([competition_row(c) for c in built]).to_csv(ROOT / "results" / "issue_table.csv", index=False, encoding="utf-8-sig")
from src.render_council import COUNCILS as _CS, render_council  # noqa: E402
(ROOT / "results" / "councils").mkdir(parents=True, exist_ok=True)
for _c in _CS:
    (ROOT / "results" / "councils" / f"{_c}.html").write_text(render_council(_c, built), encoding="utf-8")
log(f"완료: 카드 {len(built)}장, 의회 화면 {len(_CS)}개, 목차 {OUT / 'index.html'}, 결과표 results/issue_table.csv")
