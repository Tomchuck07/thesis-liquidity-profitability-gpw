"""Turns the numbers produced by r3_analysis.py into the seven charts and ten tables
that appear in Chapter 3.

r3_analysis.py computes and writes nothing; every side effect lives here, so the
analysis can be imported and reloaded without files being regenerated each time.

Styling follows the macro chart in r2_macro/main.py: same palette, figure size, grid.

Run:  uv run python r3_empirics/r3_report.py
"""

from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

import r3_analysis as a

BASE = Path(__file__).parent
OUTPUT = BASE / "output"

# Palette and geometry from the macro chart in r2_macro/main.py.
KOLORY = {"Dino": "#F7A81C", "LPP": "#333333", "CCC": "#888888"}
MARKERY = {"Dino": "o", "LPP": "s", "CCC": "^"}
ROZMIAR = (12, 6)

# Profitability ratios are shares, so their axis is a percentage. One decimal place
# keeps the smallest value legible - CCC's ROA reaches -0.4%.
FORMAT_PROCENT = mticker.PercentFormatter(xmax=1, decimals=1)


def zapisz(fig, nazwa):
    """Save settings in one place, so every chart comes out alike.

    tight_layout() gives the axis labels room inside the figure; bbox_inches="tight"
    crops what margin is left. r2_macro/main.py uses the same pair.
    """
    fig.tight_layout()
    plik = OUTPUT / nazwa
    fig.savefig(plik, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return plik


def styl_osi(ax, procent):
    """The shared look: horizontal grid only, no top or right frame."""
    ax.grid(axis="y", linestyle="--", linewidth=0.5, alpha=0.7)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    if procent:
        # xmax=1 says the data is a fraction, so 0.094 prints as 9.4% and the ratios
        # stay in their native units.
        ax.yaxis.set_major_formatter(FORMAT_PROCENT)


def rysuj_serie(ax, wskaznik):
    """Draws all three companies for one ratio onto an existing axis.

    Takes the pivot table from the analysis as it is: years in the index, one column
    per company, already in the order the thesis uses.
    """
    tabela = a.tabele[wskaznik]
    tabela.plot(
        ax=ax,
        color=[KOLORY[spolka] for spolka in tabela],
        style=[MARKERY[spolka] + "-" for spolka in tabela],
        linewidth=1.5,
        markersize=4,
    )
    ax.set_xticks(tabela.index)


def wykres_liniowy(wskaznik):
    """One ratio, three companies, six years - six of the seven charts."""
    # The axis format follows from which group the ratio belongs to.
    procent = wskaznik in a.wsk_rentownosc_names

    fig, ax = plt.subplots(figsize=ROZMIAR)
    rysuj_serie(ax, wskaznik)
    ax.set_xlabel("Rok", fontsize=11)
    ax.set_ylabel(f"{wskaznik} (%)" if procent else wskaznik, fontsize=11)
    # No set_title: in Word the caption "Wykres N." carries the title, same as the
    # macro chart. A title baked into the PNG would duplicate it.
    styl_osi(ax, procent)
    ax.legend(fontsize=9, framealpha=0.9)

    return zapisz(fig, f"wykres_{wskaznik}.png")


def wykres_dino_cr_roa():
    """Scatter plot of the one correlation that reached significance:
    Dino CR-ROA, Spearman rs = 0.8286, p = 0.0416.

    The only chart not built from a pivot table - it plots one ratio against another
    for a single company, which needs the long frame.

    The trend line is ordinary least squares; the reported coefficient is Spearman's,
    which works on ranks. Different models: the line shows direction, not the fit.
    At n = 6 they diverge - Pearson on this pair gives p = 0.0558.
    """
    dino = a.wskazniki.loc[a.wskazniki["spolka"] == "Dino"].sort_values("rok")
    x = dino["CR"].to_numpy()
    y = dino["ROA"].to_numpy()

    fig, ax = plt.subplots(figsize=ROZMIAR)
    ax.scatter(x, y, color=KOLORY["Dino"], s=60, zorder=3)

    nachylenie, wyraz = np.polyfit(x, y, 1)
    siatka = np.linspace(x.min(), x.max(), 50)
    ax.plot(
        siatka,
        nachylenie * siatka + wyraz,
        color="#333333",
        linestyle="--",
        linewidth=1.2,
        zorder=2,
    )

    # Each point is one year; without the label the reader cannot tell which.
    for xi, yi, rok in zip(x, y, dino["rok"]):
        ax.annotate(
            str(rok), (xi, yi), textcoords="offset points", xytext=(6, 4), fontsize=9
        )

    ax.set_xlabel("Wskaźnik bieżącej płynności (CR)", fontsize=11)
    ax.set_ylabel("Rentowność aktywów (ROA, %)", fontsize=11)
    # No legend here: one company, one trend line, both explained by the axis labels.
    styl_osi(ax, procent=True)

    return zapisz(fig, "wykres_Dino_CR_ROA.png")


def zapisz_tabele():
    """Writes every table the chapter reports, one CSV each.

    Three decimals for the ratios, four for the test statistics and coefficients.
    .round() only touches numeric columns, so the labels are left alone.
    """
    for nazwa, tabela in a.tabele.items():
        # The year is the index here, so it has to be written.
        tabela.round(3).to_csv(OUTPUT / f"tabela_{nazwa}.csv")

    # The index is row numbers and carries nothing.
    a.shapiro_report.round(4).to_csv(OUTPUT / "shapiro_wilk.csv", index=False)

    for spolka, tabela in a.correlation_tables.items():
        tabela.round(4).to_csv(OUTPUT / f"korelacje_{spolka}.csv")


if __name__ == "__main__":
    OUTPUT.mkdir(exist_ok=True)

    for wskaznik in a.wsk_plynnosc_names + a.wsk_rentownosc_names:
        print(f"  → {wykres_liniowy(wskaznik).name}")
    print(f"  → {wykres_dino_cr_roa().name}")

    zapisz_tabele()
    print(f"  → {len(a.tabele) + 1 + len(a.correlation_tables)} tabel CSV")
