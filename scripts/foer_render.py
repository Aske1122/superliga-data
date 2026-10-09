"""
Køres automatisk af Quarto FØR hver 'quarto render' (se pre-render i _quarto.yml).

Beregner læsetiden for hver artikel ud fra artiklens egen tekst og skriver den i artiklens
forside-metadata som 'laesetid: N'. Det tal bruges BÅDE i artikellisterne (rubrikken "7'")
og øverst i selve artiklen, så de altid er ens.

Laver også en side pr. tidligere sæson under "Superligaen i tal" (tal/<sæson>.qmd),
så der automatisk kommer en arkivside, når en ny sæson starter.

Tæller kun brødtekst: kode, metadata, grafer, margennoter og noter til forfatteren
(stikord, pladsholdere) tælles ikke med. Ca. 200 ord i minuttet.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IKKE_TEKST = ("stikord", "pladsholder", "note-til-mig", "column-margin", "column-page-right")


def laesetid(qmd: str) -> int:
    krop = qmd.split("---", 2)[2] if qmd.startswith("---") else qmd
    krop = re.sub(r"```.*?```", " ", krop, flags=re.S)                  # kodeceller og rå HTML
    # Fjern hele div-blokke, der ikke er brødtekst (fx ::: {.stikord} ... :::)
    ud, spring = [], 0
    for linje in krop.splitlines():
        if linje.startswith(":::"):
            if spring:
                spring = spring - 1 if linje.strip() == ":::" else spring + 1
                continue
            if any(k in linje for k in IKKE_TEKST):
                spring = 1
            continue
        if not spring:
            ud.append(linje)
    ord_ = re.findall(r"[\wæøåÆØÅ'-]+", "\n".join(ud))
    return max(1, round(len(ord_) / 200))


for qmd in sorted((ROOT / "posts").glob("*/index.qmd")):
    tekst = qmd.read_text(encoding="utf-8")
    minutter = laesetid(tekst)
    hoved, rest = tekst.split("---", 2)[1], tekst.split("---", 2)[2]
    ny = re.sub(r"^laesetid: .*\n", "", hoved, flags=re.M)
    ny = re.sub(r"^body-classes: .*\n", "", ny, flags=re.M)
    ny = ny.rstrip("\n") + (f"\nlaesetid: {minutter}               # beregnes automatisk (scripts/foer_render.py)"
                            f"\nbody-classes: artikelside laesetid-{minutter}\n")
    if ny != hoved:
        qmd.write_text("---" + ny + "---" + rest, encoding="utf-8")
        print(f"  læsetid: {qmd.parent.name} = {minutter} min")


# --- Sider pr. tidligere sæson under "Superligaen i tal" ---
import duckdb

db = ROOT / "data" / "clean" / "superliga.duckdb"
if db.exists():                                     # uden data (fx på en ny maskine) springes det over
    with duckdb.connect(str(db), read_only=True) as con:
        saesoner = [r[0] for r in con.sql(
            "SELECT DISTINCT saeson FROM kampe WHERE fase <> 'playoff' ORDER BY saeson DESC").fetchall()]
    for saeson in saesoner[1:]:                     # den nyeste er tal/index.qmd
        sti = ROOT / "tal" / f"{saeson.replace('/', '-')}.qmd"
        indhold = (f'---\ntitle: "Superligaen i tal {saeson}"\njupyter: superliga\nexecute:\n  echo: false\n---\n\n'
                   f'```{{python}}\nSAESON = "{saeson}"\n```\n\n{{{{< include _indhold.qmd >}}}}\n')
        if not sti.exists() or sti.read_text(encoding="utf-8") != indhold:
            sti.write_text(indhold, encoding="utf-8")
            print(f"  sæsonside: {sti.relative_to(ROOT)}")
