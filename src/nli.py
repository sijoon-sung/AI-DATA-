"""한국어 자연어 추론(NLI): (전제, 가설) 쌍의 함의·중립·모순 확률.

scripts/07_train_nli.py가 KLUE-NLI로 미세조정한 KoELECTRA(model/koelectra-klue-nli)를 쓴다.
쓰임새
  (1) 생성·템플릿 문장이 인용 원문에 의해 뒷받침되는지 검사 (전제=인용 원문, 가설=생성 문장)
  (2) "이 발언은 ○○의 정책 사례를 언급한다" 같은 가설로 제로샷 판정 (전제=발언 문단)
확률 열 순서는 LABELS(KLUE-NLI 라벨 번호 0, 1, 2)와 같다.
"""
from __future__ import annotations

import os
from pathlib import Path


import numpy as np  # noqa: E402
import torch  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "model" / "koelectra-klue-nli"
LABELS = ["entailment", "neutral", "contradiction"]
# 학습은 128 토큰으로 했지만 위치 임베딩은 512까지 사전학습되어 있어 문단(400자 안팎)이 잘리지 않게 넉넉히 둔다
MAX_LEN = 256

_loaded: dict = {}


def load_model(model_dir: str | Path = MODEL_DIR, device: str | None = None):
    """토크나이저, 모델, 장치를 돌려준다. 같은 경로·장치는 한 번만 읽어 둔다."""
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    device = device or ("cuda" if torch.cuda.is_available() else "cpu")
    key = (str(Path(model_dir).resolve()), device)
    if key not in _loaded:
        if not Path(model_dir).exists():
            raise FileNotFoundError(f"{model_dir} 가 없다. scripts/07_train_nli.py로 먼저 학습한다.")
        tok = AutoTokenizer.from_pretrained(model_dir)
        model = AutoModelForSequenceClassification.from_pretrained(model_dir).to(device).eval()
        _loaded[key] = (tok, model, device)
    return _loaded[key]


def _as_list(x, n):
    """문자열 하나면 n번 반복해 목록으로 만든다 (한 문단에 가설 여러 개를 붙일 때)."""
    return [x] * n if isinstance(x, str) else list(x)


@torch.inference_mode()
def nli_probs(premises, hypotheses, batch_size: int = 64, max_len: int = MAX_LEN,
              model_dir: str | Path = MODEL_DIR, device: str | None = None) -> np.ndarray:
    """(전제, 가설) 쌍별 [함의, 중립, 모순] 확률. 반환 shape (n, 3), 각 행의 합은 1.

    premises, hypotheses 중 하나가 문자열이면 다른 쪽 길이에 맞춰 반복한다.
    max_len을 넘으면 긴 쪽(대개 전제)부터 자른다.
    """
    n = max(1 if isinstance(premises, str) else len(premises),
            1 if isinstance(hypotheses, str) else len(hypotheses))
    prem, hyp = _as_list(premises, n), _as_list(hypotheses, n)
    if len(prem) != len(hyp):
        raise ValueError(f"전제 {len(prem)}개와 가설 {len(hyp)}개의 수가 다르다")
    if n == 0:
        return np.zeros((0, len(LABELS)), dtype=np.float32)
    tok, model, device = load_model(model_dir, device)
    # 길이순으로 묶어 패딩을 줄이고, 끝에 원래 순서로 되돌린다
    order = np.argsort([len(p) + len(h) for p, h in zip(prem, hyp)], kind="stable")
    out = np.zeros((n, len(LABELS)), dtype=np.float32)
    for i in range(0, n, batch_size):
        idx = order[i:i + batch_size]
        enc = tok([prem[j] for j in idx], [hyp[j] for j in idx], padding=True,
                  truncation="longest_first", max_length=max_len, return_tensors="pt").to(device)
        with torch.autocast(device_type="cuda", dtype=torch.float16, enabled=device.startswith("cuda")):
            logits = model(**enc).logits
        out[idx] = torch.softmax(logits.float(), dim=-1).cpu().numpy()
    return out


def entail_prob(premise: str, hypothesis: str, **kw) -> float:
    """전제가 가설을 함의할 확률 하나."""
    return float(nli_probs([premise], [hypothesis], **kw)[0, 0])
