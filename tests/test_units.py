import numpy as np
import pandas as pd
import pyvinecopulib as pv

from compound import marginals as mg
from compound import thresholds as th
from compound.copulas import fit_all, pseudo_obs, upper_tail_curve
from compound.features import add_antecedent
from compound.returnperiods import p_and, p_or, return_periods


def indep_cdf(uv):
    return uv[:, 0] * uv[:, 1]


def test_and_or_independence_closed_form():
    u, v = np.array([0.9, 0.99]), np.array([0.8, 0.95])
    assert np.allclose(p_and(u, v, indep_cdf), (1 - u) * (1 - v))
    assert np.allclose(p_or(u, v, indep_cdf), 1 - u * v)


def test_kendall_return_period_independence():
    # For the independence copula K(t) = t - t ln t.
    rng = np.random.default_rng(0)
    sample = rng.random((400_000, 2))
    u, v = np.array([0.9]), np.array([0.9])
    t = 0.81
    expected = 1.0 / (1 - (t - t * np.log(t)))
    got = return_periods(u, v, indep_cdf, sample, mu_years=1.0)["T_kendall"][0]
    assert abs(got - expected) / expected < 0.03
    rp = return_periods(u, v, indep_cdf, sample, 1.0)
    assert rp["T_or"][0] < rp["T_u"][0] < rp["T_and"][0]


def test_dahal_hasegawa_daily_threshold_is_about_144mm():
    df = pd.DataFrame({"P1": [140.0, 150.0], "P3": [0.0, 0.0], "P7": [0.0, 0.0]})
    assert list(th.dahal_hasegawa_exceed(df)) == [False, True]


def test_ecdf_transform_bounds_and_ties():
    u = mg.ecdf_transform(np.array([0, 0, 0, 1, 2, 3.0]), np.array([0, 3, 10, np.nan]))
    assert 0 < u[0] < u[1] < 1 and u[2] < 1 and np.isnan(u[3])


def test_antecedent_windows_do_not_cross_season_gap():
    d = pd.to_datetime(["2020-09-29", "2020-09-30", "2021-05-22", "2021-05-23", "2021-05-24"])
    df = pd.DataFrame({"unit": "A", "date": d, "P": [10, 10, 1, 2, 3.0], "sm": [.1, .2, .3, .4, .5]})
    out = add_antecedent(df, "P", [3], "sm", 1)
    assert np.isnan(out["P3"].iloc[2]) and out["P3"].iloc[4] == 6.0
    assert np.isnan(out["SM"].iloc[2]) and out["SM"].iloc[3] == 0.3


def test_copula_fit_recovers_gumbel_and_tail():
    true = pv.Bicop(family=pv.BicopFamily.gumbel, parameters=np.array([[2.0]]))
    u = pseudo_obs(true.sample(3000, seeds=[3]))
    fits = fit_all(u, ["gaussian", "gumbel", "clayton", "frank"])
    assert fits[0]["family"] == "gumbel"
    assert abs(fits[0]["tau"] - 0.5) < 0.05
    tail = upper_tail_curve(u, fits[0]["model"], np.array([0.95]))
    assert tail["model"][0] > 0.4


def test_gpd_return_level_monotone():
    rng = np.random.default_rng(1)
    fit = mg.fit_gpd(rng.gamma(0.8, 20, 5000), 0.9)
    rl = mg.gpd_return_level(fit, np.array([2, 10, 50]), 122)
    assert np.all(np.diff(rl) > 0)


def test_contingency_tss():
    c = th.contingency(np.array([1, 1, 0, 0]), np.array([1, 0, 1, 0]))
    assert c["TSS"] == 0.0 and c["hit_rate"] == 0.5


def test_cascade_table_matches_schema():
    import json
    from pathlib import Path
    root = Path(__file__).resolve().parents[1] / "data" / "events"
    schema = json.loads((root / "schema.json").read_text())
    df = pd.read_csv(root / "cascades.csv", dtype=str).fillna("")
    for col in schema["required"]:
        assert col in df.columns and (df[col] != "").all(), col
    for col in ("rainfall_triggered", "verification_status", "fatalities_status"):
        allowed = set(schema["properties"][col]["enum"])
        assert set(df[col]) <= allowed, (col, set(df[col]) - allowed)
