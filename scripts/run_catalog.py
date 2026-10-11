"""정책 카탈로그를 한 번에 돌린다: 점검 → 색인 → 주제 군집 → 배정 → 설명 → LLM 이름 → 가족 → 이름 묶기 → 평가.
자세한 방법과 문제 해결: docs/실행_가이드.md

실행: python scripts/run_catalog.py [--k 800] [--per-council 12000] [--skip-index] [--skip-label] [--until 2024-12-31]
  --skip-index  검색 색인(09)이 이미 다 있으면 건너뛴다(없어도 끝난 의회는 자동으로 건너뛴다)
  --skip-label  LLM 단계(label, family)를 건너뛴다(GPU 없이 빠르게 확인할 때)
  --until       그 날짜까지로 주제를 만들고, 이후 회의록은 나중에 들어온 것처럼 따로 배정한다(갱신 실험)
선행: data/processed/ (scripts/02~04). 없으면 README의 01~04 단계를 먼저 돌린다.
단계마다 실패하면 거기서 멈추고, 다시 실행하면 끝난 단계의 결과를 이어 쓴다(색인·LLM 이름은 이어서 한다).
결과: data/catalog/topics/ (eval.json, labels.jsonl, families.parquet 등)
"""
import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ap = argparse.ArgumentParser()
ap.add_argument("--k", type=int, default=800)
ap.add_argument("--per-council", type=int, default=12000)
ap.add_argument("--skip-index", action="store_true")
ap.add_argument("--skip-label", action="store_true")
ap.add_argument("--until", default=None)
args = ap.parse_args()

if not (ROOT / "data" / "processed" / "passages.parquet").exists():
    sys.exit("data/processed/passages.parquet가 없다. README의 01~04 단계를 먼저 실행한다.")

T = "scripts/15_policy_topics.py"
steps = [] if args.skip_label else [[T, "check"]]
if not args.skip_index:
    steps += [["scripts/09_build_index.py", "--part", "bm25"], ["scripts/09_build_index.py", "--part", "dense"]]
fit = [T, "fit", "--k", str(args.k), "--per-council", str(args.per_council)]
if args.until:
    nxt = (__import__("datetime").date.fromisoformat(args.until) + __import__("datetime").timedelta(days=1)).isoformat()
    steps += [fit + ["--until", args.until], [T, "assign", "--until", args.until], [T, "assign", "--since", nxt]]
else:
    steps += [fit, [T, "assign"]]
steps += [[T, "describe"]]
if not args.skip_label:
    steps += [[T, "label"], [T, "family"], [T, "names"]]
steps += [[T, "eval"]]

t0 = time.time()
for s in steps:
    print(f"\n===== [{time.time() - t0:6.0f}초] {' '.join(s)}", flush=True)
    r = subprocess.run([sys.executable, *s], cwd=ROOT)
    if r.returncode:
        sys.exit(f"실패: {' '.join(s)} (종료 코드 {r.returncode}). 고친 뒤 다시 실행하면 이어서 한다.")
print(f"\n전체 완료 ({time.time() - t0:.0f}초). 결과: data/catalog/topics/eval.json")
