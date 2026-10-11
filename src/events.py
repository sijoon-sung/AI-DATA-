"""사건표: 이슈별 근거 문단을 모으고, 각 문단이 그 이슈를 말하는지 인코더로 점수를 매긴다.

1. 후보: 이슈마다 별칭 정규식(띄어쓰기 무시)으로 문단 356만 개를 한 번 흘려 읽으며 모은다(넓게 찾기).
2. 관련 판정: bge-reranker-v2-m3(교차 인코더)로 (이슈 정의, 문단) 점수를 매긴다(정확히 판정하기).
   점수가 낮은 문단은 이름만 같은 다른 이야기(동명이의)거나 지나가는 언급일 가능성이 크다.
출력 열: issue_id, pid, doc_id, start, end, role, is_member, n_chars, text, (docs 메타), rel(관련 점수 0~1).
LLM은 쓰지 않는다.
"""
from __future__ import annotations

import os

import pandas as pd
import pyarrow.compute as pc
import pyarrow.parquet as pq

COLS = ["pid", "doc_id", "utt_idx", "start", "end", "role", "is_member", "n_chars", "text"]


def scan(passages_path, patterns: dict, docs: pd.DataFrame):
    """patterns: {issue_id: [(별칭, 정규식), ...]}. 첫 별칭이 대표 별칭이다.
    한 번 흘려 읽으며 모든 이슈·별칭의 후보 문단을 모은다. 대표 별칭보다 지나치게 많이 걸리는 별칭
    (발언에서 흔히 쓰는 말: '기반시설', '피해학생' 등)은 뺀다.
    돌려주는 값: (사건표, {issue_id: 남긴 별칭 목록}, {issue_id: {별칭: 걸린 문단 수}}).
    사건표의 alias_bits는 patterns의 원래 별칭 순서대로 어느 별칭에 걸렸는지 비트로 적은 것이다."""
    keep = set(docs.doc_id)
    out = {k: [] for k in patterns}
    for b in pq.ParquetFile(passages_path).iter_batches(columns=COLS, batch_size=100_000):
        t = b.column("text")
        for k, al in patterns.items():
            masks = [pc.match_substring_regex(t, rx) for _, rx in al]
            anym = masks[0]
            for m in masks[1:]:
                anym = pc.or_(anym, m)
            sub = b.filter(anym)
            if sub.num_rows:
                d = sub.to_pandas()
                bits = sum((pc.filter(m, anym).to_numpy(zero_copy_only=False).astype(int) << j) for j, m in enumerate(masks))
                out[k].append(d.assign(alias_bits=bits))
    frames, kept_alias, counts = [], {}, {}
    for k, parts in out.items():
        al = patterns[k]
        if not parts:
            kept_alias[k] = [a for a, _ in al]
            counts[k] = {a: 0 for a, _ in al}
            continue
        d = pd.concat(parts)
        d = d[d.doc_id.isin(keep)]
        bits = d.alias_bits.to_numpy(dtype="int64")
        cnt = [int(((bits >> j) & 1).sum()) for j in range(len(al))]
        counts[k] = {al[j][0]: cnt[j] for j in range(len(al))}
        cap = max(4 * cnt[0], 400)
        ok = [j for j in range(len(al)) if j == 0 or cnt[j] <= cap]
        mask = sum(1 << j for j in ok)
        d = d[(bits & mask) > 0]
        kept_alias[k] = [al[j][0] for j in ok]
        frames.append(d.assign(issue_id=k))
    ev = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=COLS + ["issue_id"])
    ev = ev.merge(docs, on="doc_id").sort_values(["issue_id", "date", "doc_id", "start"]).reset_index(drop=True)
    return ev, kept_alias, counts


def relevance(ev: pd.DataFrame, queries: dict, batch_size=32) -> pd.Series:
    """(이슈 정의, 문단) 관련 점수. queries: {issue_id: '정책 수단 이름과 정의'}."""
    import torch
    from sentence_transformers import CrossEncoder
    if ev.empty:
        return pd.Series(dtype=float)
    dev = "cuda" if torch.cuda.is_available() else "cpu"  # GPU가 없으면 CPU로 (느리다)
    model = CrossEncoder("BAAI/bge-reranker-v2-m3", device=dev, max_length=384,
                         model_kwargs={"torch_dtype": torch.float16 if dev == "cuda" else torch.float32})
    pairs = [(queries[i], t[:700]) for i, t in zip(ev.issue_id, ev.text)]
    s = model.predict(pairs, batch_size=batch_size, show_progress_bar=False, activation_fn=torch.nn.Sigmoid())
    del model
    torch.cuda.empty_cache()
    return pd.Series(s, index=ev.index, dtype=float)
