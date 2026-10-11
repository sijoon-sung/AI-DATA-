"""L5 확산 예측: 정책 수단마다, 아직 안건을 내지 않은 의회가 다음 6개월 안에 첫 제정 조례안을 상정하는가.

- 단위: (정책 수단, 아직 안건이 없는 의회, 기준점). 기준점 이전에 1곳 이상이 제정한 정책 수단만 대상으로 한다.
- 변수는 모두 기준점 이전 자료로 만든다(누출 차단): 이미 안건을 낸 의회 수, 최근 6개월 제정 수, 같은 권역 수,
  의회의 제정 활동률, 첫 관측 뒤 경과 개월(6개월 상한), 관찰 준비 기간에 이미 있던 수단인지.
- 모형은 로지스틱 회귀다. 월별 기준점(2024-04~)을 쌓아 학습한다.
- 백테스트: 결과 창이 겹치지 않는 기준점 2025-01-01, 2025-07-01. 보정은 라벨 없이 절편만 옮긴다
  (평가 위험 집합의 평균 예측 = 직전 기준점의 실제 기저율).
- 등급: 기저율의 5배·2배·0.5배를 미리 정한 경계로 쓰고, 백테스트에서 등급별로 실제 맞은 비율을 함께 낸다.
설계와 실험 근거: docs/04_아키텍처.md 4절, research_notes/아키텍처 구체화/forecasting.md.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
from scipy.optimize import brentq
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.preprocessing import StandardScaler

COUNCILS = ["서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종", "경기",
            "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주"]
ZONE = {"서울": "수도권", "경기": "수도권", "인천": "수도권", "대전": "충청", "세종": "충청", "충북": "충청", "충남": "충청",
        "광주": "호남", "전북": "호남", "전남": "호남", "대구": "대경", "경북": "대경", "부산": "동남", "울산": "동남",
        "경남": "동남", "강원": "강원", "제주": "제주"}
FEATS = ["n_any", "n_recent6", "zone_adopt", "activity_rate", "ms_c", "lcens"]
LOGF = {"n_any", "n_recent6", "zone_adopt", "activity_rate", "ms_c"}
DATA0 = pd.Timestamp("2024-01-01")
BURN_END = pd.Timestamp("2024-04-01")
HORIZON = 6
ORIGINS = pd.date_range("2024-04-01", "2025-07-01", freq="MS")
TESTS = [pd.Timestamp("2025-01-01"), pd.Timestamp("2025-07-01")]
FINAL = pd.Timestamp("2026-01-01")


def pair_table(pol: pd.DataFrame) -> pd.DataFrame:
    """(정책 수단, 의회)마다 첫 안건일, 첫 제정 안건일."""
    g = pol.groupby(["inst_id", "council_short"])
    t = g.date.min().rename("any_first").to_frame()
    t["enact_first"] = pol[pol.act == "제정"].groupby(["inst_id", "council_short"]).date.min()
    return t.reset_index()


def build_origin(o: pd.Timestamp, pair: pd.DataFrame, horizon=HORIZON) -> pd.DataFrame:
    end = o + pd.DateOffset(months=horizon)
    pa = pair[pair.any_first < o]
    pe = pair[pair.enact_first < o]
    seeds = np.sort(pe.inst_id.unique())
    if len(seeds) == 0:
        return pd.DataFrame()
    kf = pd.DataFrame(index=seeds)
    kf["n_any"] = pa[pa.inst_id.isin(seeds)].groupby("inst_id").size()
    kf["n_recent6"] = pe[pe.enact_first >= o - pd.DateOffset(months=6)].groupby("inst_id").size()
    kf["first_seen"] = pa[pa.inst_id.isin(seeds)].groupby("inst_id").any_first.min()
    kf = kf.fillna({"n_recent6": 0})
    kf["months_since"] = (o - kf.first_seen).dt.days / 30.4
    grid = pd.MultiIndex.from_product([seeds, COUNCILS], names=["inst_id", "council_short"]).to_frame(index=False)
    had = pa[pa.inst_id.isin(seeds)][["inst_id", "council_short"]].assign(had=1)
    grid = grid.merge(had, how="left", on=["inst_id", "council_short"])
    grid = grid[grid.had.isna()].drop(columns="had").merge(kf, left_on="inst_id", right_index=True)
    z = pa[pa.inst_id.isin(seeds)].assign(zone=lambda d: d.council_short.map(ZONE)).groupby(["inst_id", "zone"]).size()
    grid["zone"] = grid.council_short.map(ZONE)
    grid = grid.merge(z.rename("zone_adopt"), how="left", left_on=["inst_id", "zone"], right_index=True)
    grid["zone_adopt"] = grid.zone_adopt.fillna(0)
    act = pe.groupby("council_short").inst_id.nunique()
    obs_m = max((o - DATA0).days / 30.4, 1.0)
    grid["activity_rate"] = grid.council_short.map(act).fillna(0) / obs_m
    grid["ms_c"] = grid.months_since.clip(upper=6)
    grid["lcens"] = (grid.first_seen < BURN_END).astype(int)
    ef = grid.merge(pair[["inst_id", "council_short", "enact_first"]], how="left",
                    on=["inst_id", "council_short"]).enact_first
    grid["y"] = ((ef >= o) & (ef < end)).astype(int).values
    grid["o"] = o
    return grid.drop(columns=["zone", "first_seen"])


def _X(d):
    m = d[FEATS].astype("float64").copy()
    for f in FEATS:
        if f in LOGF:
            m[f] = np.log1p(m[f].clip(lower=0))
    return m.values


def fit(train: pd.DataFrame):
    sc = StandardScaler().fit(_X(train))
    lr = LogisticRegression(max_iter=3000).fit(sc.transform(_X(train)), train.y)
    return lambda d: lr.predict_proba(sc.transform(_X(d)))[:, 1], (sc, lr)


def prior_shift(p, rate):
    z = np.log(np.clip(p, 1e-9, 1 - 1e-9) / (1 - np.clip(p, 1e-9, 1 - 1e-9)))
    b = brentq(lambda b: (1 / (1 + np.exp(-(z + b)))).mean() - rate, -15, 15)
    return 1 / (1 + np.exp(-(z + b)))


def grade(p, b0):
    return np.select([p >= 5 * b0, p >= 2 * b0, p >= 0.5 * b0], ["상", "중", "하"], "최하")


def wilson(k, n, z=1.96):
    if n == 0:
        return (float("nan"), float("nan"))
    ph = k / n
    d = 1 + z * z / n
    c = (ph + z * z / (2 * n)) / d
    h = z * math.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / d
    return (c - h, c + h)


def run(pol: pd.DataFrame) -> dict:
    """백테스트와 최종 예측. 결과: metrics(백테스트), grades(등급별 실측 빈도), final(최종 예측 표), b0."""
    pair = pair_table(pol)
    panel = pd.concat([build_origin(o, pair) for o in ORIGINS], ignore_index=True)
    rows, pooled = [], []
    for T in TESTS:
        tr = panel[panel.o + pd.DateOffset(months=HORIZON) <= T]
        te = panel[panel.o == T]
        prev = panel[panel.o == T - pd.DateOffset(months=HORIZON)]
        if tr.empty or te.empty or te.y.nunique() < 2:
            continue
        f, _ = fit(tr)
        b = prev.y.mean()
        p = prior_shift(f(te), b)
        auc = roc_auc_score(te.y, p)
        bs, bs0 = brier_score_loss(te.y, p), brier_score_loss(te.y, np.full(len(te), b))
        # 같은 정책 수단 안에서 어느 의회가 먼저 할지 가리는 힘(사건과 비사건이 모두 있는 수단만)
        w = [roc_auc_score(g.y, g.p) for _, g in te.assign(p=p).groupby("inst_id") if g.y.nunique() == 2]
        rows.append(dict(origin=str(T.date()), pairs=len(te), events=int(te.y.sum()), base_rate=round(float(te.y.mean()), 4),
                         auc=round(float(auc), 3), brier_skill=round(float(1 - bs / bs0), 3),
                         within_auc=round(float(np.mean(w)), 3) if w else None, within_n=len(w)))
        pooled.append(te.assign(p=p, g=grade(p, b)))
    pool = pd.concat(pooled)
    grades = {}
    for gname in ["상", "중", "하", "최하"]:
        s = pool[pool.g == gname]
        lo, hi = wilson(int(s.y.sum()), len(s))
        grades[gname] = dict(n=len(s), hits=int(s.y.sum()), rate=round(float(s.y.mean()), 4) if len(s) else None,
                             ci=[round(lo, 4), round(hi, 4)])
    # 최종 예측: 2026-01-01 기준점, 2025-07-01까지의 기준점으로 학습
    tr = panel[panel.o + pd.DateOffset(months=HORIZON) <= FINAL]
    f, (sc, lr) = fit(tr)
    b0 = float(panel[panel.o == FINAL - pd.DateOffset(months=HORIZON)].y.mean())
    fin = build_origin(FINAL, pair)
    fin["p"] = prior_shift(f(fin), b0)
    fin["grade"] = grade(fin.p.values, b0)
    coef = dict(zip(FEATS, np.round(lr.coef_[0], 3).tolist()))
    return dict(metrics=rows, grades=grades, b0=b0, final=fin, coef=coef, pair=pair)
