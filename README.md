# Superliga-data

Quarto-website med dataanalyser af Superligaen.

## Mapper
- `scripts/` – datahentning. **Alle API-kald går gennem `scripts/budget_guard.py`.**
- `data/raw/` – JSON-svar fra API'erne (cache, aldrig på GitHub)
- `data/clean/` – rensede tabeller (Parquet/DuckDB, aldrig på GitHub)
- `posts/` – artikler (én mappe pr. artikel med `index.qmd`, `figurer/` og `deling/`)
- `scripts/analyse.py` – fælles beregninger (game states, alternativ tabel, scoringstidspunkter, comebacks)
- `scripts/stil.py` – husstilen for alle grafer (se `stiltest.qmd`)
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
    .venv/bin/python scripts/analyse.py        # beregn analysetabeller (an_*) i data/clean
    quarto preview --profile kladde            # se siden INKL. kladder (kun lokalt, bygger til _kladde/)
    quarto render                              # byg den offentlige side til docs/ (kladder udelades)

## Nye artikler
1. Kopiér mappen `posts/2026-10-foeringer-der-forsvinder/` som skabelon.
2. Behold `jupyter: superliga` og `draft: true` i toppen, indtil artiklen er klar.
3. Grafer laves med `stil.figur(...)` og gemmes med `stil.gem(...)`.

## Første gang på en ny maskine
    .venv/bin/python -m ipykernel install --sys-prefix --name superliga   # Python-kerne til Quarto

## Design
- `styles.scss` – hele sidens design (farver, skrifter, forside, kort, artikler). Farverne står øverst.
- `_skabeloner/forside.ejs` og `_skabeloner/arkiv.ejs` – hvordan artikelkortene ser ud.
- `_partials/skrifter.html` – skrifttyperne Oswald, Inter og Source Serif 4.
  **Før siden går online:** de hentes i dag fra Google Fonts. Af hensyn til GDPR bør filerne ligge lokalt i projektet.
- `scripts/efter_render.py` – kører efter `quarto render` og fjerner kladdernes billeder fra `docs/`.
