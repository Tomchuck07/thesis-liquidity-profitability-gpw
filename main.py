"""Macro pipeline: builds a combined table of CPI, the NBP reference rate, and
retail-sales dynamics for Poland (2019-2024) and renders the combination chart.

Run:  uv run python main.py   ->  output/wykres_makro.png
Note: fetches the NBP rates live over the internet.
"""

import pandas as pd
import requests
import xml.etree.ElementTree as ET
from deflator_analysis import RtA9
import matplotlib.pyplot as plt

# GUS file: 'cp1250' encoding + ';' separator (comma is the decimal mark)
CPI_raw = pd.read_csv('data/CPI.csv', encoding='cp1250', sep=';')

CPI = (
    CPI_raw.query('Rok.between(2019,2024)')
    .assign(Wartość = lambda df_: df_.Wartość.str.replace(',','.').astype(float))
    .loc[:,['Rok','Wartość']]
    .set_index('Rok')
    .rename(columns={'Wartość':'CPI'})
)


# NBP publishes historical rates only as XML (no CSV/API)
response = requests.get('https://static.nbp.pl/dane/stopy/stopy_procentowe_archiwum.xml')
root = ET.fromstring(response.content)

wyniki = []

for pozycje in root.findall('.//pozycje'):
    data = pozycje.attrib
    for pozycja in pozycje.findall('.//pozycja'):
        stopy = pozycja.attrib
        wyniki.append({**data, **stopy})

intrR_raw = pd.DataFrame(wyniki)

# As of 31 December each year — rates apply from one update to the next, so we take the most recent update before year-end
intrR = (
    intrR_raw.assign(obowiazuje_od = lambda df_: df_.obowiazuje_od.astype('datetime64[ns]'),
                     oprocentowanie = lambda df_: df_.oprocentowanie.str.replace(',','.').astype(float))
            .query('id=="ref"')
            .set_index('obowiazuje_od')
            .asof([pd.Timestamp(year, 12, 31) for year in range(2019,2025)])
            .rename(index = lambda x: x.year, columns={'oprocentowanie': 'stopa_referencyjna'})
            .drop(columns='id')
)

# Final table; CPI-100 and RtA9-100 (percentage change instead of index) - standardizing the scale to allow a single y-axis on the graph
final_macro = (
    (CPI-100).join([
        intrR.loc[:,'stopa_referencyjna'],
        RtA9.loc[:,'komunikaty_gus_dynamika_realna']-100
    ])
    .rename(columns={'komunikaty_gus_dynamika_realna': 'dynamika_sprzedazy_detalicznej_ceny_stale'})
)

fig, ax = plt.subplots(figsize=(12, 6))

# Bars - Retail Sales
ax.bar(final_macro.index,
       final_macro['dynamika_sprzedazy_detalicznej_ceny_stale'],
       color='#F7A81C',
       label='Zmiana procentowa sprzedaży detalicznej (ceny stałe, r/r)',
       zorder=2,
       width=0.6)

# CPI line
ax.plot(final_macro.index, final_macro['CPI'],
        color='#333333',
        linewidth=1.5,
        marker='o',
        markersize=4,
        label='Inflacja CPI (średnioroczna, %)')

# NBP reference rate line
ax.plot(final_macro.index, final_macro['stopa_referencyjna'],
        color='#888888',
        linestyle='--',
        linewidth=1.5,
        marker='o',
        markersize=4,
        label='Stopa referencyjna NBP (stan na 31 grudnia, %)')

# Baseline 0
ax.axhline(y=0, color='black', linewidth=0.8, linestyle='-')

# Axis and grid
ax.set_xlabel('Rok', fontsize=11)
ax.set_ylabel('%', fontsize=11)
ax.set_xticks(final_macro.index)
ax.grid(axis='y', linestyle='--', linewidth=0.5, alpha=0.7)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

# Legend
ax.legend(fontsize=9, framealpha=0.9)

plt.tight_layout()
plt.savefig('output/wykres_makro.png', dpi=300, bbox_inches='tight')
plt.show()
