"""7단계: KLUE-NLI로 KoELECTRA를 미세조정해 한국어 NLI(함의 판정) 모델을 만든다.

기반 모델: monologg/koelectra-base-v3-discriminator (Apache-2.0)
학습 자료: klue/klue nli (CC BY-SA 4.0). train 24,998쌍으로 학습, validation 3,000쌍으로 평가
  라벨 0=함의(entailment), 1=중립(neutral), 2=모순(contradiction)
출력 model/koelectra-klue-nli/
  model.safetensors(가중치, git 제외), config.json, 토크나이저 파일
  metrics.json: 설정, 에폭별 학습 로그, 최고 에폭의 검증 정확도·클래스별 F1·혼동행렬·출처별 정확도
검증 정확도가 가장 높은 에폭을 저장한다. 두 자료는 Hugging Face 캐시에서 읽고, 없으면 처음 한 번 내려받는다
(인터넷 없이 돌리려면 HF_HUB_OFFLINE=1을 설정한다).
주의: 별도 시험셋이 없어 에폭 선택과 평가를 같은 validation으로 하므로 보고 정확도는 약간 낙관적이다.
"""
import json
import os
import random
import sys
import time
from pathlib import Path

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import torch  # noqa: E402
import transformers  # noqa: E402
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_recall_fscore_support  # noqa: E402
from torch.utils.data import DataLoader  # noqa: E402
from transformers import AutoModelForSequenceClassification, AutoTokenizer  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.nli import LABELS, MODEL_DIR  # noqa: E402

BASE = "monologg/koelectra-base-v3-discriminator"
HF_HUB = Path(os.environ.get("HF_HUB_CACHE", Path.home() / ".cache" / "huggingface" / "hub"))
SEED = 20261011
EPOCHS = 3
LR = 3e-5
BATCH = 32
EVAL_BATCH = 128
MAX_LEN = 128
WARMUP = 0.1        # 전체 스텝 중 학습률을 올리는 비율
WEIGHT_DECAY = 0.01
LOG_EVERY = 100     # 몇 스텝마다 학습 손실을 출력할지


def set_seed(seed):
    """파이썬·넘파이·토치 난수를 모두 고정한다."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def klue_nli(split):
    """KLUE-NLI parquet 하나를 읽는다(캐시에 없으면 klue/klue 데이터셋에서 nli 폴더만 내려받는다)."""
    from huggingface_hub import snapshot_download
    root = Path(snapshot_download(repo_id="klue/klue", repo_type="dataset", allow_patterns=["nli/*"]))
    files = sorted(root.glob(f"nli/{split}-*.parquet"))
    if not files:
        raise FileNotFoundError(f"{root} 아래에 klue/klue nli {split} 파일이 없다")
    df = pd.read_parquet(files[-1])
    assert {"premise", "hypothesis", "label"} <= set(df.columns), df.columns.tolist()
    return df


def encode(tok, df):
    """문장 쌍을 토큰화한다. 패딩은 배치마다 따로 한다."""
    enc = tok(df.premise.tolist(), df.hypothesis.tolist(), truncation=True, max_length=MAX_LEN)
    return [{"input_ids": a, "token_type_ids": b, "attention_mask": c, "labels": y}
            for a, b, c, y in zip(enc["input_ids"], enc["token_type_ids"], enc["attention_mask"], df.label)]


def collate(batch):
    """배치 안에서 가장 긴 길이에 맞춰 0으로 패딩한다 ([PAD] id = 0)."""
    n = max(len(x["input_ids"]) for x in batch)
    out = {k: torch.tensor([x[k] + [0] * (n - len(x[k])) for x in batch])
           for k in ("input_ids", "token_type_ids", "attention_mask")}
    out["labels"] = torch.tensor([x["labels"] for x in batch])
    return out


@torch.inference_mode()
def evaluate(model, loader, device):
    """검증 손실과 예측 라벨."""
    model.eval()
    preds, loss_sum, n = [], 0.0, 0
    for b in loader:
        b = {k: v.to(device) for k, v in b.items()}
        with torch.autocast(device_type="cuda", dtype=torch.float16):
            out = model(**b)
        loss_sum += out.loss.item() * len(b["labels"])
        n += len(b["labels"])
        preds.append(out.logits.argmax(-1).cpu().numpy())
    model.train()
    return loss_sum / n, np.concatenate(preds)


def main():
    t0 = time.time()
    set_seed(SEED)
    device = "cuda"
    assert torch.cuda.is_available(), "GPU가 필요하다"
    torch.cuda.reset_peak_memory_stats()

    tr, va = klue_nli("train"), klue_nli("validation")
    print("학습", len(tr), tr.label.value_counts().sort_index().to_dict(),
          "| 검증", len(va), va.label.value_counts().sort_index().to_dict(), flush=True)
    tok = AutoTokenizer.from_pretrained(BASE)
    tr_ds, va_ds = encode(tok, tr), encode(tok, va)
    n_trunc = sum(len(x["input_ids"]) >= MAX_LEN for x in tr_ds)
    print(f"토큰화 {time.time() - t0:.0f}초, {MAX_LEN} 토큰에서 잘린 학습 쌍 {n_trunc}개", flush=True)

    g = torch.Generator().manual_seed(SEED)
    tr_dl = DataLoader(tr_ds, batch_size=BATCH, shuffle=True, collate_fn=collate, generator=g)
    va_dl = DataLoader(va_ds, batch_size=EVAL_BATCH, shuffle=False, collate_fn=collate)

    model = AutoModelForSequenceClassification.from_pretrained(
        BASE, num_labels=len(LABELS),
        id2label=dict(enumerate(LABELS)), label2id={lab: i for i, lab in enumerate(LABELS)}).to(device)
    # 편향과 LayerNorm에는 가중치 감쇠를 걸지 않는다
    decay = [p for n, p in model.named_parameters() if not (n.endswith("bias") or "LayerNorm" in n)]
    no_decay = [p for n, p in model.named_parameters() if n.endswith("bias") or "LayerNorm" in n]
    opt = torch.optim.AdamW([{"params": decay, "weight_decay": WEIGHT_DECAY},
                             {"params": no_decay, "weight_decay": 0.0}], lr=LR)
    total = EPOCHS * len(tr_dl)
    warm = int(WARMUP * total)
    # 선형 워밍업 뒤 선형 감소
    sched = torch.optim.lr_scheduler.LambdaLR(
        opt, lambda s: s / max(1, warm) if s < warm else max(0.0, (total - s) / max(1, total - warm)))
    scaler = torch.amp.GradScaler("cuda")

    log, best, step = [], None, 0
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    model.train()
    for ep in range(1, EPOCHS + 1):
        te, run, run_n, ep_loss = time.time(), 0.0, 0, 0.0
        for b in tr_dl:
            b = {k: v.to(device, non_blocking=True) for k, v in b.items()}
            with torch.autocast(device_type="cuda", dtype=torch.float16):
                loss = model(**b).loss
            opt.zero_grad(set_to_none=True)
            scaler.scale(loss).backward()
            scaler.unscale_(opt)
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            scaler.step(opt)
            scaler.update()
            sched.step()
            step += 1
            run += loss.item(); run_n += 1; ep_loss += loss.item()
            if step % LOG_EVERY == 0:
                print(f"  에폭 {ep} 스텝 {step}/{total} 손실 {run / run_n:.4f} "
                      f"학습률 {sched.get_last_lr()[0]:.2e}", flush=True)
                run, run_n = 0.0, 0
        va_loss, pred = evaluate(model, va_dl, device)
        acc = accuracy_score(va.label, pred)
        mf1 = f1_score(va.label, pred, average="macro")
        rec = {"epoch": ep, "train_loss": round(ep_loss / len(tr_dl), 4), "val_loss": round(va_loss, 4),
               "val_acc": round(acc, 4), "val_macro_f1": round(mf1, 4), "sec": round(time.time() - te, 1)}
        log.append(rec)
        print(f"[에폭 {ep}] 학습 손실 {rec['train_loss']} 검증 손실 {rec['val_loss']} "
              f"정확도 {acc:.4f} 매크로 F1 {mf1:.4f} ({rec['sec']}초)", flush=True)
        if best is None or acc > best["acc"]:
            best = {"epoch": ep, "acc": acc, "pred": pred}
            model.save_pretrained(MODEL_DIR)
            tok.save_pretrained(MODEL_DIR)
            print(f"  최고 정확도 갱신, {MODEL_DIR} 에 저장", flush=True)

    # 최고 에폭 기준 최종 지표
    y, pred = va.label.to_numpy(), best["pred"]
    p, r, f, s = precision_recall_fscore_support(y, pred, labels=range(len(LABELS)), zero_division=0)
    per_class = {LABELS[i]: {"precision": round(p[i], 4), "recall": round(r[i], 4), "f1": round(f[i], 4),
                             "support": int(s[i])} for i in range(len(LABELS))}
    cm = confusion_matrix(y, pred, labels=range(len(LABELS)))
    by_source = {src: round(accuracy_score(g_.label, pred[g_.index]), 4)
                 for src, g_ in va.reset_index(drop=True).groupby("source")} if "source" in va else {}
    elapsed = time.time() - t0
    mem = {"max_allocated_gb": round(torch.cuda.max_memory_allocated() / 2**30, 2),
           "max_reserved_gb": round(torch.cuda.max_memory_reserved() / 2**30, 2)}
    metrics = {
        "base_model": BASE, "base_model_license": "Apache-2.0",
        "train_data": "klue/klue nli train", "eval_data": "klue/klue nli validation",
        "data_license": "CC BY-SA 4.0",
        "labels": dict(enumerate(LABELS)),
        "config": {"seed": SEED, "epochs": EPOCHS, "lr": LR, "batch_size": BATCH, "max_len": MAX_LEN,
                   "warmup_ratio": WARMUP, "weight_decay": WEIGHT_DECAY, "fp16": True, "grad_clip": 1.0,
                   "n_train": len(tr), "n_val": len(va), "train_pairs_truncated": n_trunc},
        "log": log,
        "best_epoch": best["epoch"],
        "val_accuracy": round(accuracy_score(y, pred), 4),
        "val_macro_f1": round(f1_score(y, pred, average="macro"), 4),
        "per_class": per_class,
        "confusion_matrix": {"rows_true_cols_pred": LABELS, "matrix": cm.tolist()},
        "val_accuracy_by_source": by_source,
        "note": "에폭 선택과 평가를 같은 validation으로 해서 정확도가 약간 낙관적이다",
        "runtime_sec": round(elapsed, 1), "gpu": torch.cuda.get_device_name(0), "gpu_memory": mem,
        "versions": {"torch": torch.__version__, "transformers": transformers.__version__},
    }
    (MODEL_DIR / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n최고 에폭 {best['epoch']} | 검증 정확도 {metrics['val_accuracy']:.4f} "
          f"매크로 F1 {metrics['val_macro_f1']:.4f}")
    for k, v in per_class.items():
        print(f"  {k:<13} P {v['precision']:.4f} R {v['recall']:.4f} F1 {v['f1']:.4f}")
    print("혼동행렬 (행=정답, 열=예측,", "/".join(LABELS) + ")")
    print(cm)
    print("출처별 정확도", by_source)
    print(f"실행 시간 {elapsed / 60:.1f}분 | GPU 최대 메모리 할당 {mem['max_allocated_gb']}GB, "
          f"예약 {mem['max_reserved_gb']}GB")


if __name__ == "__main__":
    main()
