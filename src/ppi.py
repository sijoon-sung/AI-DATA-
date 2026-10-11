"""Prediction-Powered Inference(PPI/PPI++): 적은 사람 정답과 많은 자동 판정으로 비율(정밀도 등)의 신뢰구간을 낸다.

본보기: Angelopoulos, Bates, Fannjiang, Jordan, Zrnic (2023) "Prediction-Powered Inference" (arXiv:2301.09633),
        Angelopoulos, Duchi, Zrnic (2023) "PPI++" (arXiv:2311.01453), 구현 ppi_py(github.com/aangelopoulos/ppi_py, MIT)의
        ppi_mean_pointestimate / ppi_mean_ci와 같은 식이다. ARES(Saad-Falcon et al. 2024)도 같은 방식으로 판정기 편향을 고친다.

  θ̂_λ = mean(λ·f(X_unl)) + mean(Y − λ·f(X_lab))
  SE   = sqrt( var(λ·f_unl)/N + var(Y − λ·f_lab)/n ),  z 구간
  λ    = 분산을 최소화하는 값을 [0, 1]로 자른다(λ=0이면 사람 정답만 쓴 고전 추정, λ=1이면 기본 PPI).
층화 표본: 검수 표본은 층(출처 × 점수 구간)마다 뽑았으므로 층마다 추정하고 모집단 비중 N_h/N으로 합친다
(층별 추정량의 분산도 같은 비중의 제곱으로 합친다). 정답 표본은 층 안에서 무작위여야 한다.
"""
from __future__ import annotations

import math

import numpy as np

Z = {0.05: 1.959964, 0.1: 1.644854}


def _lam(y, f_lab, f_unl):
    n, N = len(y), len(f_unl)
    if n < 2 or np.var(f_lab) == 0:
        return 0.0
    f_all = np.concatenate([f_lab, f_unl])
    cov = np.cov(y, f_lab)[0, 1]
    lam = cov / ((1 + n / N) * np.var(f_all, ddof=1))
    return float(min(max(lam, 0.0), 1.0))


def ppi_mean(y, f_lab, f_unl, alpha=0.05, lam=None):
    """한 모집단의 평균(비율). y: 사람 정답(0/1), f_lab: 같은 표본의 자동 판정, f_unl: 나머지 전체의 자동 판정.
    돌려주는 값: dict(est, lo, hi, se, lam, n, N, classical=(est, lo, hi))."""
    y, f_lab, f_unl = (np.asarray(a, dtype=float) for a in (y, f_lab, f_unl))
    n, N = len(y), len(f_unl)
    lam = _lam(y, f_lab, f_unl) if lam is None else lam
    est = lam * f_unl.mean() + (y - lam * f_lab).mean()
    se = math.sqrt((np.var(lam * f_unl, ddof=1) if N > 1 else 0.0) / max(N, 1) + np.var(y - lam * f_lab, ddof=1) / n) if n > 1 else float("nan")
    z = Z.get(alpha, 1.959964)
    c_se = math.sqrt(y.var(ddof=1) / n) if n > 1 else float("nan")
    return {"est": est, "lo": est - z * se, "hi": est + z * se, "se": se, "lam": lam, "n": n, "N": N,
            "classical": (y.mean(), y.mean() - z * c_se, y.mean() + z * c_se)}


def ppi_stratified(strata: dict, alpha=0.05):
    """strata: {층: (y, f_lab, f_unl)}. 층마다 PPI로 추정하고 모집단 크기 비중으로 합친다."""
    parts = {h: ppi_mean(*v, alpha=alpha) for h, v in strata.items() if len(v[0]) >= 2}
    Ntot = sum(r["N"] + r["n"] for r in parts.values())
    est = sum((r["N"] + r["n"]) / Ntot * r["est"] for r in parts.values())
    se = math.sqrt(sum(((r["N"] + r["n"]) / Ntot) ** 2 * r["se"] ** 2 for r in parts.values()))
    cl = sum((r["N"] + r["n"]) / Ntot * r["classical"][0] for r in parts.values())
    z = Z.get(alpha, 1.959964)
    return {"est": est, "lo": est - z * se, "hi": est + z * se, "se": se, "classical_est": cl, "strata": parts}
