# Superliga-data

Quarto-website med dataanalyser af Superligaen.

## Mapper
- `scripts/` – datahentning. **Alle API-kald går gennem `scripts/budget_guard.py`.**
- `data/raw/` – JSON-svar fra API'erne (cache, aldrig på GitHub)
- `data/clean/` – rensede tabeller (Parquet/DuckDB, aldrig på GitHub)
- `posts/` – artikler
- `docs/` – det færdige website (genereres af `quarto render`, publiceres via GitHub Pages)

## Kom i gang
    python3 -m venv .venv
    .venv/bin/pip install -r requirements.txt
    cp .env.example .env        # og indsæt nøgler
    .venv/bin/python scripts/budget_guard.py   # vis dagens API-forbrug
    quarto preview              # se websitet lokalt
