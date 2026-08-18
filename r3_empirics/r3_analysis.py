"""Empirical part of the thesis: liquidity vs profitability of three retail
companies listed on the WSE (Dino, LPP, CCC), 2019-2024.

Computes six ratios, tests every series for normality, and correlates each
liquidity ratio with each profitability ratio.

Source data: r3_empirics/data/dane_R3.csv - 162 figures taken from the companies'
consolidated annual reports (thousands of PLN), each one checked against the source
and recomputed in a spreadsheet before use. The script starts from that finished
CSV; it does not parse the reports themselves.

This module only computes. It writes nothing and prints nothing, so it is safe
to import repeatedly from a notebook or from r3_report.py, which handles the
formatting, the tables and the charts.

Run:  uv run python r3_empirics/r3_analysis.py
"""

from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

BASE = Path(__file__).parent

df = pd.read_csv(BASE / "data" / "dane_R3.csv")


# Ordered categories fix the company and ratio order for every table, sort and chart
# downstream. Without them pandas falls back to alphabetical.
spolki_cat = pd.CategoricalDtype(categories=["Dino", "LPP", "CCC"], ordered=True)
wsk_plynnosc_names = ["CR", "QR", "ChR"]
wsk_rentownosc_names = ["ROS", "ROA", "ROE"]
wsk_cat = pd.CategoricalDtype(
    categories=wsk_plynnosc_names + wsk_rentownosc_names, ordered=True
)
# Significance threshold for the normality test and the correlations, set before the
# results are seen.
ALFA = 0.05

# Ratio definitions: thesis, section 1.3.
wskazniki = df.assign(
    spolka=df["spolka"].astype(spolki_cat),
    CR=df["aktywa_obrotowe"] / df["zob_krotkoterm"],
    QR=(df["aktywa_obrotowe"] - df["zapasy"] - df["rmc"]) / df["zob_krotkoterm"],
    ChR=df["inwestycje_krotkoterm"] / df["zob_krotkoterm"],
    ROS=df["zysk_netto"] / df["przychody"],
    ROA=df["zysk_netto"] / df["aktywa_ogolem"],
    ROE=df["zysk_netto"] / df["kapital_wlasny"],
).loc[:, ["spolka", "rok", "CR", "QR", "ChR", "ROS", "ROA", "ROE"]]

# Checks the data, not the code. CR, QR and ChR share a denominator with a progressively
# narrower numerator, so CR >= QR >= ChR holds by definition and a breach means a figure
# landed in the wrong column while being copied from the reports. ROE vs ROA is not
# checked: under a net loss ROE falls below ROA, which is a finding, not an invariant.
zle_qr = wskazniki.loc[wskazniki["QR"] > wskazniki["CR"], ["spolka", "rok"]]
zle_chr = wskazniki.loc[wskazniki["ChR"] > wskazniki["QR"], ["spolka", "rok"]]

assert zle_qr.empty, f"QR > CR - sprawdz dane:\n{zle_qr}"
assert zle_chr.empty, f"ChR > QR - sprawdz dane:\n{zle_chr}"


# One table per ratio (years x companies). After the pivot each column is the six-year
# series for one company, which is what the normality test takes.
tabele = {}

wsk_names = wskazniki.columns.drop(["rok", "spolka"])

for wskaznik in wsk_names:
    tabele[wskaznik] = wskazniki.pivot_table(
        index="rok", columns="spolka", values=wskaznik
    ).rename_axis(columns=None)


wyniki = []

for wsk, tabela in tabele.items():
    for firma in tabela:
        sw = stats.shapiro(tabela[firma])
        wyniki.append(
            {
                "wskaznik": wsk,
                "spolka": firma,
                "W": sw.statistic,
                "p": sw.pvalue,
            }
        )

# Shapiro-Wilk is reported as evidence for the choice of method, not used as a switch.
shapiro_report = (
    pd.DataFrame(wyniki)
    .astype({"spolka": spolki_cat, "wskaznik": wsk_cat})
    .sort_values(by=["spolka", "wskaznik"])
    .assign(normality_assumption=lambda df_: df_["p"] > ALFA)
    .reset_index(drop=True)
)

# Spearman for all 27 pairs: CCC's ROE holds an extreme value (SW p = 0.0096), n = 6 is
# too small to lean on a normality assumption, and coefficients from different methods
# would not be comparable across one table. Full reasoning in the README.
correlation_tables = {}

for s in spolki_cat.categories.to_list():
    res = stats.spearmanr(wskazniki.loc[wskazniki.spolka == s, wsk_names])
    rs_values = pd.DataFrame(res.statistic, index=wsk_names, columns=wsk_names).loc[
        wsk_plynnosc_names, wsk_rentownosc_names
    ]
    p_values = pd.DataFrame(res.pvalue, index=wsk_names, columns=wsk_names).loc[
        wsk_plynnosc_names, wsk_rentownosc_names
    ]

    # .stack() walks the matrix row by row, giving the pair order used in the thesis:
    # CR-ROS, CR-ROA, CR-ROE, QR-ROS, and so on.
    correlation_tables[s] = (
        pd.concat({"rs": rs_values.stack(), "p": p_values.stack()}, axis=1)
        .rename_axis(["wsk_plynnosci", "wsk_rentownosci"])
        .assign(
            istotnosc=lambda df_: np.where(df_.p < ALFA, "istotna", "nieistotna"),
            # Guilford's scale; thresholds and wording from the thesis, section 1.3.
            sila=lambda df_: pd.cut(
                df_.rs.abs(),
                bins=[0, 0.2, 0.4, 0.7, 0.9, 1],
                labels=[
                    "brak lub znikoma",
                    "słaba",
                    "umiarkowana",
                    "silna",
                    "bardzo silna",
                ],
            ),
            kierunek=lambda df_: np.where(df_.rs > 0, "dodatnia", "ujemna"),
        )
    )
