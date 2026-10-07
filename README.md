# Superliga-data

Quarto-website med dataanalyser af Superligaen.

## Mapper
- `scripts/` – datahentning. **Alle API-kald går gennem `scripts/budget_guard.py`.**
- `data/raw/` – JSON-svar fra API'erne (cache, aldrig på GitHub)
- `data/clean/` – rensede tabeller (Parquet/DuckDB, aldrig på GitHub)
- `posts/` – artikler
- `scripts/holdnavne.csv` – oversætter hver kildes holdnavne til vores egne (hold_id + hold)

## Datakilder
- **Sportmonks** (hovedkilde, 2020/21–2026/27). Superligaen = liga 271.
- **API-Football** (reserve/krydstjek, gratis kun 2022–2024). Superligaen = liga 119.
- `docs/` – det færdige website (genereres af `quarto render`, publiceres via GitHub Pages)

## Kom i gang
    python3 -m venv .venv
    .venv/bin/pip install -r requirements.txt
    cp .env.example .env        # og indsæt nøgler
    .venv/bin/python scripts/budget_guard.py   # vis dagens API-forbrug
    .venv/bin/python scripts/hent_sportmonks.py --plan   # vis hvad en hentning vil koste
    .venv/bin/python scripts/hent_sportmonks.py          # hent nye kampe (spørger om lov)
    .venv/bin/python scripts/rens.py           # rådata -> data/clean (ingen forespørgsler)
    .venv/bin/python scripts/kvalitet.py       # datakvalitetstjek
    quarto preview              # se websitet lokalt
