"""DSI433 Group 4 — Slide 09: Reinsurance Analysis & Live Demo (Streamlit).

Run:  streamlit run app.py
Data: data/province_rp_losses.csv  (Track A output of DSI433_Full_CAT_Modeling.ipynb)
UI:   template.html                (web-app layout; numbers are injected by this script)
Track B and the reinsurance replay are the same code as notebook sections 8, 9 and 11
(banded synthetic catalog, common-shock share alpha, compound Poisson, SEED 433),
so the default settings reproduce the notebook numbers exactly.
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="DSI433 G4 · Reinsurance Decision Support", page_icon="🌊", layout="wide", initial_sidebar_state="collapsed")
DATA = Path(__file__).parent / "data"
NATIVE_RPS = [10, 20, 50, 75, 100, 200, 500]       # RP250 is interpolated -> not used for severity
SUBDIVISIONS, SEED = 12, 433
BLUE, ORANGE, GREY, GREEN, RED = "#1F5E8C", "#DB9157", "#9E9E9E", "#1F7A4C", "#B5341F"


# ---------------------------------------------------------------- data
@st.cache_data
def load():
    prov = pd.read_csv(DATA / "province_rp_losses.csv", dtype={"province_code": str})
    prov["province_code"] = prov["province_code"].str.zfill(2)
    wide = prov.pivot(index="province_code", columns="return_period", values="estimated_economic_loss_usd").sort_index()
    expo = prov[prov.return_period == 10].set_index("province_code").loc[wide.index, "exposure_value_usd"].to_numpy()
    return wide, expo


wide, EXPOSURE = load()
CODES = wide.index.to_numpy()
P_NATIVE = 1 / np.array(NATIVE_RPS[::-1], dtype=float)
LOSS_NATIVE = wide[NATIVE_RPS].to_numpy()[:, ::-1]


# ---------------------------------------------------------------- Track B (same as notebook section 8–9)
@st.cache_data
def build_catalog(p0=0.20, tail_multiplier=1.0, subdivisions=SUBDIVISIONS):
    p_nodes = np.r_[0.0, P_NATIVE, p0]
    rare = np.minimum(LOSS_NATIVE[:, 0] * tail_multiplier, EXPOSURE)
    loss_nodes = np.column_stack([rare, LOSS_NATIVE, np.zeros(len(EXPOSURE))])
    q_nodes = -np.log1p(-p_nodes)
    q_edges = np.concatenate([np.linspace(a, b, subdivisions, endpoint=False)
                              for a, b in zip(q_nodes[:-1], q_nodes[1:])] + [q_nodes[-1:]])
    rate = np.diff(q_edges)
    mean_p = 1 - np.exp(-q_edges[:-1]) * (-np.expm1(-rate)) / rate
    severity = np.vstack([np.interp(mean_p, p_nodes, row) for row in loss_nodes])
    return rate, severity


@st.cache_data(show_spinner="กำลังจำลองเหตุการณ์…")
def simulate(p0, tail_multiplier, alpha, n_years, seed=SEED):
    """Returns per-event (year, loss) so that reinsurance layers can be applied per event."""
    rate, severity = build_catalog(p0, tail_multiplier)
    lam = rate.sum()
    weights = rate / lam
    rng = np.random.default_rng(seed)
    groups = []
    if alpha > 0:
        groups.append((alpha, severity.sum(axis=0)))
    if alpha < 1:
        groups.extend((1 - alpha, s) for s in severity)
    years, losses = [], []
    for share, sev in groups:
        n = rng.poisson(share * lam, size=n_years)
        idx = np.repeat(np.arange(n_years), n)
        if len(idx):
            band = rng.choice(len(weights), size=len(idx), p=weights)
            years.append(idx)
            losses.append(sev[band])
    year = np.concatenate(years)
    loss = np.concatenate(losses)
    annual = np.bincount(year, weights=loss, minlength=n_years)
    occ = np.zeros(n_years)
    np.maximum.at(occ, year, loss)
    analytical = float(severity.sum(axis=0) @ rate)
    prov_aal = severity @ rate
    return year, loss, annual, occ, analytical, prov_aal


def q(x, rp):
    return float(np.quantile(x, 1 - 1 / rp))


def ep_xy(x):
    s = np.sort(x)
    p = (len(s) - np.searchsorted(s, s, side="right")) / len(s)
    m = p > 0
    return s[m], p[m]


# ---------------------------------------------------------------- fixed baseline (same as notebook)
P0, TAIL, ALPHA, N_YEARS = 0.20, 1.0, 0.5, 100_000
SHARE, PAYOUT = 0.01, 0.80

st.markdown("""<style>
#MainMenu, header, footer, [data-testid="stSidebar"], [data-testid="collapsedControl"], [data-testid="stToolbar"] {display:none !important;}
.block-container {padding:0 !important; max-width:100% !important;}
[data-testid="stAppViewContainer"], .stApp {background:#F3F6F9;}
iframe {display:block;}
</style>""", unsafe_allow_html=True)

# ---------------------------------------------------------------- compute (identical to notebook section 11)
year, loss, annual, occ, _, _ = simulate(P0, TAIL, ALPHA, N_YEARS)
factor = SHARE * PAYOUT
ins, gross, occ_ins = loss * factor, annual * factor, occ * factor
exhaust = np.quantile(occ_ins, 0.996)
ceded = {"No Reinsurance": np.zeros_like(gross)}
for r in (10, 25, 50):
    R = np.quantile(occ_ins, 1 - 1 / r)
    ceded[f"XoL RP{r}–250"] = np.bincount(year, weights=np.clip(ins - R, 0, max(0.0, exhaust - R)), minlength=N_YEARS)
ceded["Quota Share 30%"] = gross * 0.3
TAGS = {"No Reinsurance": ("NONE", ""), "Quota Share 30%": ("QS", "q")}
data = [{"n": k, "t": TAGS.get(k, ("XoL", "x"))[0], "c": TAGS.get(k, ("XoL", "x"))[1],
         "pml": round(float(np.quantile(gross - c, 0.996)) / 1e6, 2),
         "aal": round(float((gross - c).mean()) / 1e6, 2),
         "ced": round(float(c.mean()) / 1e6, 2)} for k, c in ceded.items()]

# ---------------------------------------------------------------- render the web-app UI (template.html)
html = (Path(__file__).parent / "template.html").read_text(encoding="utf-8").replace("__DATA__", json.dumps(data, ensure_ascii=False))
if hasattr(st, "iframe"):          # Streamlit >= 1.52
    st.iframe(html, height=1010)
else:
    components.html(html, height=1010, scrolling=True)
