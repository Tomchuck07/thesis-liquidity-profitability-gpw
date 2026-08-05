"""Retail-sales module + deflator investigation.

Builds two series — full population (SnG_all) and firms with >9 employees (RtA9)
— and tests whether the >9 real dynamics can be reconstructed with an implied
deflator borrowed from the full population. The check showed the error grows with
inflation, so the official GUS figures (gus_official) are used instead — see README.

Exposes: RtA9  (imported by main.py).
"""

import pandas as pd

retail_above9_raw = pd.read_csv('data/growth rate/sales_above9.csv', sep=';')
sales_growth_all_raw = pd.read_csv('data/growth rate/sales_growth_all.csv', sep=';')


SnG_all = (
    sales_growth_all_raw.loc[:,['typ_informacji', 'id_daty', 'wartosc']]
    .assign(id_daty = lambda df_: df_['id_daty'].astype(int),
            wartosc = lambda df_: df_['wartosc'].str.replace(',','.').astype(float))
    .pivot_table(index=['id_daty'], columns=['typ_informacji'], values=['wartosc'])
    .droplevel(0, axis=1)
    .rename_axis(None, axis=1)
    .rename(columns={
                    '[mln zł]': 'sprzedaz_mln_pln',
                    'okres poprzedni=100 ceny stałe [-]': 'dynamika_realna'
    })
    .assign(
        dynamika_nominalna = lambda df_: df_['sprzedaz_mln_pln']/df_['sprzedaz_mln_pln'].shift(1)*100,
        deflator = lambda df_: df_['dynamika_nominalna']/df_['dynamika_realna']*100
    )
)
# Source: GUS, reports on retail sales growth in December of each year
# The data covers companies with more than 9 employees
# Period: January–December of each year, constant prices, previous year = 100
gus_official = {
    2019: 105.4,
    2020: 96.9,
    2021: 108.1,
    2022: 105.0,
    2023: 97.3,
    2024: 102.7
}

RtA9 = (
    retail_above9_raw.T
                    .iloc[2:-1]
                    .rename(columns={0:'sprzedaz_tysZl'},
                            index= lambda x: int(x.split(';')[1]))
                    .assign(
                        sprzedaz_tysZl = lambda df_: df_.iloc[:,0].str.replace(',','.').astype(float),
                        dynamika_nominalna = lambda df_: df_['sprzedaz_tysZl']/df_['sprzedaz_tysZl'].shift(1)*100,
                    )
                    .join(SnG_all['deflator'])
                    .rename(columns = {'deflator':'deflator_impl'})
                    .assign(
                        dynamika_realna_sim = lambda df_: df_['dynamika_nominalna']/df_['deflator_impl']*100,
                        komunikaty_gus_dynamika_realna = gus_official,
                        odchylenie_symulacji =  lambda df_: df_['dynamika_realna_sim']-df_['komunikaty_gus_dynamika_realna']
                    )
)
