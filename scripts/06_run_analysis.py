"""Core analysis: marginals, copula dependence, return periods, conditional probability,
and out-of-sample skill of rainfall-only vs compound warning rules.

Input   data/processed/unit_day.parquet
Output  figures/fig01..fig07*.png, results/summary.json, results/summary.md,
        results/landslide_day_return_periods.csv
Run     python scripts/06_run_analysis.py [--quick] [--table PATH] [--outdir DIR]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy.stats import norm  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from compound import copulas as cop  # noqa: E402
from compound import marginals as mg  # noqa: E402
from compound import thresholds as th  # noqa: E402
from compound.config import load_config, p  # noqa: E402
from compound.returnperiods import return_periods  # noqa: E402

# Validated categorical slots (dataviz reference palette, light mode) + neutral inks.
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
plt.rcParams.update({
    "figure.dpi": 150, "savefig.bbox": "tight", "font.size": 9, "axes.edgecolor": INK2,
    "axes.labelcolor": INK, "xtick.color": INK2, "ytick.color": INK2, "axes.grid": True,
    "grid.color": GRID, "grid.linewidth": 0.6, "axes.spines.top": False,
    "axes.spines.right": False, "legend.frameon": False, "lines.linewidth": 2,
    "axes.axisbelow": True,
})


OUT = {"fig": "figures", "res": "results"}


def save(fig, name):
    fig.savefig(p(f"{OUT['fig']}/{name}.png"))
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="fewer bootstrap replicates")
    ap.add_argument("--table", default="data/processed/unit_day.parquet")
    ap.add_argument("--outdir", default="", help="write figures/ and results/ under this folder")
    args = ap.parse_args()
    if args.outdir:
        OUT.update(fig=f"{args.outdir}/figures", res=f"{args.outdir}/results")
    cfg = load_config()
    A = cfg["analysis"]
    nboot = 30 if args.quick else A["bootstrap_n"]
    rng_seed = A["random_seed"]
    xname, yname = A["primary_pair"]
    q = A["exceedance_quantile"]

    df = pd.read_parquet(p(args.table))
    df = df.dropna(subset=[xname, yname, "P1", "P7"]).reset_index(drop=True)
    train = df["year"].isin(cfg["split"]["train_years"])
    test = df["year"].isin(cfg["split"]["test_years"])
    days_per_season = df.groupby(["unit", "year"]).size().median()
    mu = 1.0 / days_per_season
    R: dict = {"n_unit_days": int(len(df)), "n_units": int(df["unit"].nunique()),
               "n_landslide_days": int(df["L"].sum()), "base_rate": float(df["L"].mean()),
               "precip_source": str(df["precip_source"].iloc[0]),
               "label_source": str(df["label_source"].iloc[0]), "variables": [xname, yname]}

    # ---- 1. reporting-bias check -----------------------------------------------------
    per_year = df.groupby("year")["L"].sum()
    per_month = df.groupby(df["date"].dt.month)["L"].sum()
    fig, ax = plt.subplots(1, 2, figsize=(9, 3))
    ax[0].bar(per_year.index, per_year.values, color=BLUE, width=0.7)
    ax[0].set(title="Reported landslide unit-days per monsoon", xlabel="Year", ylabel="Unit-days",
              xticks=per_year.index[::2])
    ax[1].bar(per_month.index, per_month.values, color=BLUE, width=0.7)
    ax[1].set(title="By month", xlabel="Month", xticks=per_month.index)
    save(fig, "fig01_reporting")
    R["landslide_days_per_year"] = {int(k): int(v) for k, v in per_year.items()}

    # ---- 2. marginals: pseudo-observations per unit (train ECDF) ---------------------
    df["U"] = mg.per_unit_uniform(df, xname, train)
    df["V"] = mg.per_unit_uniform(df, yname, train)
    df = df.dropna(subset=["U", "V"]).reset_index(drop=True)
    train = df["year"].isin(cfg["split"]["train_years"])
    test = df["year"].isin(cfg["split"]["test_years"])

    top = df.groupby("unit")["L"].sum().idxmax()
    xs = df.loc[(df["unit"] == top) & train, xname].to_numpy()
    gfit = mg.fit_gpd(xs, q)
    mrl = mg.mean_residual_life(xs, np.quantile(xs, np.linspace(0.5, 0.98, 40)))
    stab = mg.parameter_stability(xs, np.linspace(0.8, 0.97, 12))
    Ts = np.array([2, 5, 10, 25, 50])
    rl = mg.gpd_return_level(gfit, Ts, days_per_season)
    fig, ax = plt.subplots(1, 3, figsize=(11, 3))
    ax[0].plot(mrl["u"], mrl["mean_excess"], color=BLUE)
    ax[0].fill_between(mrl["u"], mrl["mean_excess"] - mrl["ci"], mrl["mean_excess"] + mrl["ci"],
                       color=BLUE, alpha=0.15, lw=0)
    ax[0].axvline(gfit["threshold"], color=INK2, ls="--", lw=1)
    ax[0].set(title=f"Mean residual life, {xname} ({top})", xlabel="Threshold (mm)",
              ylabel="Mean excess (mm)")
    ax[1].plot(stab["q"], stab["shape"], "o-", color=BLUE, ms=4)
    ax[1].set(title="GPD shape vs threshold quantile", xlabel="Quantile", ylabel="Shape ξ")
    ax[2].plot(Ts, rl, "o-", color=BLUE, ms=4)
    ax[2].set(xscale="log", title="GPD return levels", xlabel="Return period (years)",
              ylabel=f"{xname} (mm)")
    save(fig, "fig03_marginals")
    R["gpd_example"] = {"unit": top, **gfit,
                        "return_levels_mm": dict(zip(Ts.tolist(), np.round(rl, 1).tolist()))}

    # ---- 3. copula on all train days vs landslide days --------------------------------
    u_all = df.loc[train, ["U", "V"]].to_numpy()
    u_ls = cop.pseudo_obs(df.loc[train & (df["L"] == 1), ["U", "V"]].to_numpy())
    fits = cop.fit_all(u_all, A["copula_families"])
    best = fits[0]
    gof = cop.cvm_gof(u_all, best["model"], n_boot=min(nboot, 100), seed=rng_seed)
    fits_ls = cop.fit_all(u_ls, A["copula_families"]) if len(u_ls) >= 50 else []
    qs = np.linspace(0.80, 0.98, 10)
    tail_all = cop.upper_tail_curve(u_all, best["model"], qs)
    R["copula_all_days"] = {"table": [{k: v for k, v in f.items() if k != "model"} for f in fits],
                            "best": best["family"], "gof": gof,
                            "kendall_tau_empirical": float(pd.Series(u_all[:, 0]).corr(
                                pd.Series(u_all[:, 1]), method="kendall"))}
    if fits_ls:
        R["copula_landslide_days"] = {
            "n": int(len(u_ls)), "best": fits_ls[0]["family"],
            "table": [{k: v for k, v in f.items() if k != "model"} for f in fits_ls]}

    fig, ax = plt.subplots(1, 2, figsize=(9, 3.4))
    hb = ax[0].hexbin(df.loc[train, "U"], df.loc[train, "V"], gridsize=35, cmap="Blues",
                      mincnt=1, linewidths=0)
    ls = df.loc[train & (df["L"] == 1)]
    ax[0].scatter(ls["U"], ls["V"], s=9, color=ORANGE, edgecolor="white", lw=0.4,
                  label="Landslide unit-day")
    ax[0].set(xlabel=f"U = F({xname})", ylabel=f"V = F({yname}, t-1)",
              title="Pseudo-observations, train years")
    ax[0].legend(loc="lower left")
    fig.colorbar(hb, ax=ax[0], label="All unit-days")
    ax[1].plot(qs, tail_all["empirical"], "o-", color=BLUE, ms=4, label="Empirical")
    ax[1].plot(qs, tail_all["model"], color=ORANGE, label=f"{best['family']} copula")
    ax[1].plot(qs, 1 - qs, color=INK2, ls=":", lw=1.2, label="Independence")
    ax[1].set(title="Upper tail dependence λ(q)", xlabel="q", ylabel="P(V > q | U > q)")
    ax[1].legend()
    save(fig, "fig02_dependence")

    fig, ax = plt.subplots(figsize=(5, 2.8))
    aic0 = fits[0]["aic"]
    names = [f["family"] for f in fits]
    ax.barh(names[::-1], [f["aic"] - aic0 for f in fits][::-1], color=BLUE, height=0.6)
    ax.set(xlabel="ΔAIC vs best (lower is better)", title="Copula family comparison, all days")
    save(fig, "fig04_copula_aic")

    # ---- 4. conditional probability surface -------------------------------------------
    grid = np.round(np.linspace(0.5, 0.95, 10), 3)
    surf = th.conditional_surface(df.loc[train, "U"].to_numpy(), df.loc[train, "V"].to_numpy(),
                                  df.loc[train, "L"].to_numpy(), grid, n_boot=min(nboot, 50),
                                  seed=rng_seed)
    fig, ax = plt.subplots(figsize=(5.2, 4.2))
    im = ax.imshow(surf["p"] / surf["base_rate"], origin="lower", cmap="Blues", aspect="auto",
                   extent=[grid[0], grid[-1], grid[0], grid[-1]])
    fig.colorbar(im, ax=ax, label="P(landslide | U>a, V>b) / base rate")
    ax.set(xlabel=f"a (quantile of {xname})", ylabel=f"b (quantile of {yname})",
           title="Landslide likelihood ratio, train years")
    ax.grid(False)
    save(fig, "fig05_conditional_probability")
    Ltr, Utr_, Vtr_ = (df.loc[train, c].to_numpy() for c in ("L", "U", "V"))
    R["conditional_probability"] = {
        "base_rate": surf["base_rate"],
        "P_given_U>0.9": float(Ltr[Utr_ > 0.9].mean()),
        "P_given_U>0.9_V>0.9": float(Ltr[(Utr_ > 0.9) & (Vtr_ > 0.9)].mean()),
        "P_given_U>0.9_V<=0.5": float(Ltr[(Utr_ > 0.9) & (Vtr_ <= 0.5)].mean()),
        "P_given_U>0.95_V>0.95": float(Ltr[(Utr_ > 0.95) & (Vtr_ > 0.95)].mean())}

    # ---- 5. return periods at observed landslide days ---------------------------------
    model = best["model"]
    sample = model.sample(200_000, seeds=[rng_seed])
    lsd = df.loc[df["L"] == 1].copy()
    rp = return_periods(lsd["U"].to_numpy(), lsd["V"].to_numpy(), model.cdf, sample, mu)
    for k, v in rp.items():
        lsd[k] = v
    lsd[["unit", "date", "n_events", "deaths", xname, yname, "U", "V", *rp.keys()]] \
        .sort_values("deaths", ascending=False) \
        .to_csv(p(f"{OUT['res']}/landslide_day_return_periods.csv"), index=False)
    fig, ax = plt.subplots(figsize=(6, 3.2))
    bins = np.logspace(-2, 3, 40)
    for key, col, lab in [("T_u", INK2, f"{xname} alone"), ("T_or", BLUE, "OR"),
                          ("T_and", ORANGE, "AND"), ("T_kendall", AQUA, "Kendall")]:
        ax.hist(np.clip(lsd[key], 1e-2, 1e3), bins=bins, histtype="step", color=col, lw=1.8,
                label=lab)
    ax.set(xscale="log", xlabel="Return period (years)", ylabel="Landslide unit-days",
           title="Hazard level of observed landslide days")
    ax.legend()
    save(fig, "fig06_return_periods")
    R["return_periods_median_years"] = {k: float(np.median(v)) for k, v in rp.items()}

    # ---- 6. out-of-sample skill ----------------------------------------------------------
    y_tr, y_te = df.loc[train, "L"].to_numpy(), df.loc[test, "L"].to_numpy()
    Utr, Vtr = df.loc[train, "U"].to_numpy(), df.loc[train, "V"].to_numpy()
    Ute, Vte = df.loc[test, "U"].to_numpy(), df.loc[test, "V"].to_numpy()
    a_uni = th.tune_univariate(Utr, y_tr)
    a_b, b_b = th.tune_bivariate(Utr, Vtr, y_tr)
    z = lambda u: norm.ppf(np.clip(u, 1e-4, 1 - 1e-4))  # noqa: E731
    Xtr = np.column_stack([z(Utr), z(Vtr), z(Utr) * z(Vtr)])
    Xte = np.column_stack([z(Ute), z(Vte), z(Ute) * z(Vte)])
    lr_c = LogisticRegression(max_iter=1000).fit(Xtr, y_tr)
    lr_p = LogisticRegression(max_iter=1000).fit(Xtr[:, :1], y_tr)
    s_c, s_p = lr_c.predict_proba(Xte)[:, 1], lr_p.predict_proba(Xte[:, :1])[:, 1]
    cut_c = np.quantile(lr_c.predict_proba(Xtr)[:, 1], 1 - np.mean(Utr >= a_uni))
    rules = {
        "Dahal–Hasegawa ID": th.dahal_hasegawa_exceed(df.loc[test]),
        f"{xname} ≥ q{a_uni:.2f}": Ute >= a_uni,
        f"{xname} ≥ q{a_b:.2f} & {yname} ≥ q{b_b:.2f}": (Ute >= a_b) & (Vte >= b_b),
        "Logistic (rain+soil), same alarm rate": s_c >= cut_c,
    }
    test_years = df.loc[test, "year"].to_numpy()
    rng = np.random.default_rng(rng_seed)
    skill = {}
    for name, pred in rules.items():
        c = th.contingency(pred, y_te)
        boots = []
        yrs = np.unique(test_years)
        for _ in range(nboot):
            pick = rng.choice(yrs, len(yrs), replace=True)
            idx = np.concatenate([np.flatnonzero(test_years == y) for y in pick])
            boots.append(th.contingency(pred[idx], y_te[idx])["TSS"])
        c["TSS_90ci"] = [float(np.nanpercentile(boots, 5)), float(np.nanpercentile(boots, 95))]
        skill[name] = c
    R["skill_test_years"] = skill
    R["auc_test"] = {"rain_only_logistic": th.auc(s_p, y_te),
                     "rain_plus_soil_logistic": th.auc(s_c, y_te)}
    # AUC gain from soil moisture, with a year-block bootstrap (resample whole test years).
    gain = [th.auc(s_c[idx], y_te[idx]) - th.auc(s_p[idx], y_te[idx])
            for idx in (np.concatenate([np.flatnonzero(test_years == y)
                                        for y in rng.choice(yrs, len(yrs), replace=True)])
                        for _ in range(nboot))]
    R["auc_test"]["gain"] = R["auc_test"]["rain_plus_soil_logistic"] - R["auc_test"]["rain_only_logistic"]
    R["auc_test"]["gain_90ci"] = [float(np.nanpercentile(gain, 5)), float(np.nanpercentile(gain, 95))]
    # Mean AUC within each test year: removes between-year differences in reporting effort.
    a_p = {int(y): th.auc(s_p[test_years == y], y_te[test_years == y]) for y in yrs}
    a_c = {int(y): th.auc(s_c[test_years == y], y_te[test_years == y]) for y in yrs}
    R["auc_test_within_year"] = {
        "rain_only_logistic": float(np.nanmean(list(a_p.values()))),
        "rain_plus_soil_logistic": float(np.nanmean(list(a_c.values()))),
        "gain_by_year": {y: a_c[y] - a_p[y] for y in a_p},
    }
    R["tuned_rules"] = {"univariate_q": a_uni, "bivariate_q": [a_b, b_b]}

    fig, ax = plt.subplots(figsize=(6.4, 2.8))
    names = list(skill)
    vals = [skill[n]["TSS"] for n in names]
    lo = [skill[n]["TSS"] - skill[n]["TSS_90ci"][0] for n in names]
    hi = [skill[n]["TSS_90ci"][1] - skill[n]["TSS"] for n in names]
    ax.barh(names[::-1], vals[::-1], xerr=[lo[::-1], hi[::-1]], color=BLUE, height=0.55,
            error_kw={"ecolor": INK2, "lw": 1})
    ax.axvline(0, color=INK2, lw=0.8)
    ax.set(xlabel="True skill statistic (test years, 90% year-bootstrap CI)",
           title="Warning-rule skill, out of sample")
    save(fig, "fig07_skill")

    # ---- write results -------------------------------------------------------------------
    def clean(o):
        if isinstance(o, dict):
            return {str(k): clean(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [clean(v) for v in o]
        if isinstance(o, (np.floating, float)):
            return None if not np.isfinite(o) else round(float(o), 5)
        if isinstance(o, np.integer):
            return int(o)
        return o
    R = clean(R)
    p(f"{OUT['res']}/summary.json").write_text(json.dumps(R, indent=2, ensure_ascii=False))
    lines = [
        "# Results summary", "",
        f"- Unit-days: {R['n_unit_days']:,} across {R['n_units']} units; landslide unit-days: "
        f"{R['n_landslide_days']:,} (base rate {R['base_rate']:.4f})",
        f"- Rainfall: {R['precip_source']}; labels: {R['label_source']}",
        f"- Best copula (all train days): **{R['copula_all_days']['best']}**, Kendall τ = "
        f"{R['copula_all_days']['kendall_tau_empirical']:.3f}, CvM p = "
        f"{R['copula_all_days']['gof']['p_value']:.3f}",
        f"- P(landslide | U>0.9) = {R['conditional_probability']['P_given_U>0.9']}; "
        f"with wet soil (V>0.9) = {R['conditional_probability']['P_given_U>0.9_V>0.9']}; "
        f"with dry soil (V<=0.5) = {R['conditional_probability']['P_given_U>0.9_V<=0.5']}; "
        f"base rate {R['conditional_probability']['base_rate']:.4f}",
        f"- AUC on test years: rain only {R['auc_test']['rain_only_logistic']}, "
        f"rain + soil {R['auc_test']['rain_plus_soil_logistic']}; gain {R['auc_test']['gain']} "
        f"(90% year-bootstrap CI {R['auc_test']['gain_90ci']}); within-year mean AUC "
        f"{R['auc_test_within_year']['rain_only_logistic']} vs "
        f"{R['auc_test_within_year']['rain_plus_soil_logistic']}", "",
        "| Rule (test years) | Hit rate | False alarm rate | TSS | TSS 90% CI |",
        "|---|---|---|---|---|",
    ]
    for n, c in R["skill_test_years"].items():
        lines.append(f"| {n} | {c['hit_rate']} | {c['false_alarm_rate']} | {c['TSS']} | "
                     f"{c['TSS_90ci']} |")
    p(f"{OUT['res']}/summary.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
