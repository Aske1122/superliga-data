"""
Analysemodul: alle beregninger samlet ét sted, så artiklerne kan importere dem.

Brug i en artikel (eller i Python):
    import sys; sys.path.insert(0, "scripts")      # (sti relativt til projektmappen)
    import analyse
    kh = analyse.kamp_hold()                        # én række pr. hold pr. kamp
    gs = analyse.game_states(kh)                    # minutter foran/uafgjort/bagud

Kør hele modulet for at beregne og gemme alle tabeller i data/clean:
    .venv/bin/python scripts/analyse.py

VIGTIGE VALG (forklaret nærmere i GODMORGEN.md og på metodesiden):
  * En kamp er 90 minutter lang. Mål i tillægstid lægges på periodens sidste
    minut (45+2 tæller som minut 45, 90+4 som minut 90). Vi kender ikke den
    faktiske tillægstid, kun minuttet for hændelser, så 90 minutter er det
    eneste mål, der er ens for alle kampe.
  * Forlænget spilletid (kun 3 playoff-kampe om Europa) tælles ikke med.
    Playoff-kampene er ikke en del af ligaen og udelades af alle tabeller.
  * Ligaen deles i "grundspil" (alle møder alle) og "slutspil"
    (mesterskabs- eller nedrykningsspil). "hele_saesonen" er begge dele.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CLEAN = ROOT / "data" / "clean"

KAMPLAENGDE = 90                      # minutter pr. kamp (se valg ovenfor)
STOP_MINUTTER = [15, 30, 45, 60, 75]  # til "den alternative tabel"
INTERVALLER = [                       # til scoringstidspunkter: (navn, fra, til) inkl. begge ender
    ("0–15", 0, 15), ("16–30", 16, 30), ("31–45+", 31, 45),
    ("46–60", 46, 60), ("61–75", 61, 75), ("76–90+", 76, 90),
]
FASE_GRUPPE = {"grundspil": "grundspil", "mesterskabsspil": "slutspil", "nedrykningsspil": "slutspil"}


# ---------------------------------------------------------------------------
# 1. Indlæsning
# ---------------------------------------------------------------------------
def _hent(sql: str) -> pd.DataFrame:
    """Kør en SQL-forespørgsel mod vores lokale database (ingen API-kald)."""
    with duckdb.connect(str(CLEAN / "superliga.duckdb"), read_only=True) as con:
        return con.sql(sql).df()


def laes_kampe(til: tuple[str, int] | None = None) -> pd.DataFrame:
    """
    Ligakampe (playoff udeladt) med en ekstra kolonne 'fase_gruppe'.
    til=("2026/27", 9) giver kun data til og med runde 9 i 2026/27 (og alle tidligere sæsoner).
    Bruges til at fryse artikler: deres tal ændrer sig ikke, når nye runder kommer ind.
    """
    kampe = _hent("SELECT * FROM kampe WHERE fase <> 'playoff'")
    if til is not None:
        saeson, runde = til
        kampe = kampe[(kampe.saeson < saeson) | ((kampe.saeson == saeson) & (kampe.runde <= runde))]
    kampe["fase_gruppe"] = kampe["fase"].map(FASE_GRUPPE)
    return kampe.reset_index(drop=True)


def data_til_fra_artikel(qmd: str | Path = "index.qmd") -> tuple[str, int]:
    """
    Læs artiklens fastfrosne datagrænse fra dens forside-metadata:
        data-saeson: "2026/27"
        data-til-runde: 9
    Kodecellerne kører i artiklens mappe, så standardstien er artiklens egen index.qmd.
    """
    import re
    hoved = Path(qmd).read_text(encoding="utf-8").split("---")[1]
    saeson = re.search(r'^data-saeson:\s*"?([0-9]{4}/[0-9]{2})"?', hoved, re.M)
    runde = re.search(r"^data-til-runde:\s*([0-9]+)", hoved, re.M)
    if not (saeson and runde):
        raise ValueError(f"{qmd} mangler 'data-saeson' og/eller 'data-til-runde' i forside-metadata")
    return saeson.group(1), int(runde.group(1))


def laes_maal() -> pd.DataFrame:
    """
    Mål i ordinær tid med et 'tidspunkt' på 0–90-skalaen.
    Tillægstid: et mål i 45+2 får tidspunkt 45, et mål i 90+4 får tidspunkt 90.
    """
    maal = _hent("SELECT * FROM maal WHERE periode <= 2")
    graense = np.where(maal["periode"] == 1, 45, 90)          # periodens sidste ordinære minut
    maal["tidspunkt"] = np.minimum(maal["minut"], graense)
    # Rækkefølge inden for samme minut: tillægsminut, og derefter den samlede stilling
    maal["_samlet"] = maal["stilling_hjemme"] + maal["stilling_ude"]
    return maal.sort_values(["kamp_id", "tidspunkt", "tillaegsminut", "_samlet"])


# ---------------------------------------------------------------------------
# 2. Kerneberegning: én række pr. hold pr. kamp
# ---------------------------------------------------------------------------
def _point(for_: int, imod: int) -> int:
    return 3 if for_ > imod else 1 if for_ == imod else 0


def _forloeb(kamp_maal: pd.DataFrame, side: str) -> list[tuple[int, int, int]]:
    """
    Kampens stillingsforløb set fra ét holds side: [(tidspunkt, mål_for, mål_imod), ...]
    Første element er altid (0, 0, 0) = kampstart.
    """
    forloeb = [(0, 0, 0)]
    for r in kamp_maal.itertuples():
        h, u = r.stilling_hjemme, r.stilling_ude
        forloeb.append((r.tidspunkt, h, u) if side == "hjemme" else (r.tidspunkt, u, h))
    return forloeb


def kamp_hold(til: tuple[str, int] | None = None) -> pd.DataFrame:
    """
    Grundtabellen, som alle analyser bygger på. For hvert hold i hver kamp:
      - minutter foran / uafgjort / bagud (summer altid til 90)
      - mål og point efter 90 minutter, og point hvis kampen var stoppet efter 15, 30, ... 75
      - mål for/imod i hvert 15-minutters interval
      - om holdet var bagud / foran på et tidspunkt, og om det scorede først
    til=("2026/27", 9): kun data til og med runde 9 i 2026/27 (se laes_kampe).
    """
    kampe = laes_kampe(til)
    maal = laes_maal()
    maal_pr_kamp = dict(tuple(maal.groupby("kamp_id")))
    tom = maal.iloc[0:0]

    rows = []
    for k in kampe.itertuples():
        km = maal_pr_kamp.get(k.kamp_id, tom)
        for side in ("hjemme", "ude"):
            hold_id = k.hjemme_id if side == "hjemme" else k.ude_id
            modstander = k.ude_id if side == "hjemme" else k.hjemme_id
            forloeb = _forloeb(km, side)

            # --- Game states: læg minutterne sammen mellem hvert mål ---
            minutter = {"foran": 0, "uafgjort": 0, "bagud": 0}
            for (t0, f, i), (t1, _, _) in zip(forloeb, forloeb[1:] + [(KAMPLAENGDE, 0, 0)]):
                tilstand = "foran" if f > i else "bagud" if f < i else "uafgjort"
                minutter[tilstand] += t1 - t0

            # --- Stillingen på et bestemt tidspunkt (et mål PÅ tidspunktet tæller med) ---
            def stilling_ved(t: int) -> tuple[int, int]:
                f, i = 0, 0
                for tt, ff, ii in forloeb:
                    if tt <= t:
                        f, i = ff, ii
                return f, i

            maal_for, maal_imod = stilling_ved(KAMPLAENGDE)
            row = {
                "kamp_id": k.kamp_id, "saeson": k.saeson, "runde": k.runde, "fase": k.fase, "fase_gruppe": k.fase_gruppe,
                "kickoff_utc": k.kickoff_utc, "hold_id": hold_id, "modstander_id": modstander, "side": side,
                "min_foran": minutter["foran"], "min_uafgjort": minutter["uafgjort"], "min_bagud": minutter["bagud"],
                "maal_for": maal_for, "maal_imod": maal_imod, "point": _point(maal_for, maal_imod),
                "var_bagud": any(f < i for _, f, i in forloeb),
                "var_foran": any(f > i for _, f, i in forloeb),
                "scorede_foerst": len(forloeb) > 1 and forloeb[1][1] == 1,
                "modstander_scorede_foerst": len(forloeb) > 1 and forloeb[1][2] == 1,
            }
            for t in STOP_MINUTTER:
                row[f"point_{t}"] = _point(*stilling_ved(t))

            # --- Mål for/imod pr. 15-minutters interval ---
            for navn, fra, til in INTERVALLER:
                row[f"for_{navn}"] = row[f"imod_{navn}"] = 0
            forrige = (0, 0)
            for tt, ff, ii in forloeb[1:]:
                for navn, fra, til in INTERVALLER:
                    if fra <= tt <= til:
                        row[f"for_{navn}"] += ff - forrige[0]
                        row[f"imod_{navn}"] += ii - forrige[1]
                forrige = (ff, ii)
            rows.append(row)

    kh = pd.DataFrame(rows)
    # Holdnavne fra vores navnetabel (fulde navne til tabeller, forkortelser til grafer)
    navne = pd.read_csv(ROOT / "scripts" / "holdnavne.csv").drop_duplicates("hold_id")[["hold_id", "hold"]]
    return kh.merge(navne, on="hold_id", how="left")


# ---------------------------------------------------------------------------
# 3. Kontrol
# ---------------------------------------------------------------------------
def kontroller(kh: pd.DataFrame) -> pd.DataFrame:
    """
    Returnerer kampe der fejler mindst ét tjek (bør være tom):
      1) foran + uafgjort + bagud = 90 for hvert hold i hver kamp
      2) holdets minutter foran = modstanderens minutter bagud
      3) mål efter 90 min fra forløbet = kampens officielle resultat efter 90 min
    """
    fejl = kh[kh[["min_foran", "min_uafgjort", "min_bagud"]].sum(axis=1) != KAMPLAENGDE].assign(tjek="sum≠90")

    h = kh[kh.side == "hjemme"].set_index("kamp_id")
    u = kh[kh.side == "ude"].set_index("kamp_id")
    spejl = h.index[(h.min_foran != u.min_bagud) | (h.min_bagud != u.min_foran)]
    fejl = pd.concat([fejl, kh[kh.kamp_id.isin(spejl)].assign(tjek="spejl")])

    kampe = laes_kampe().set_index("kamp_id")
    forkert = h.index[(h.maal_for != kampe.loc[h.index, "hjemme_maal_90"])
                      | (h.maal_imod != kampe.loc[h.index, "ude_maal_90"])]
    return pd.concat([fejl, kh[kh.kamp_id.isin(forkert)].assign(tjek="resultat")])


# ---------------------------------------------------------------------------
# 4. Analyser (A–D). Alle tager grundtabellen og returnerer én række pr. sæson/fase-gruppe/hold
# ---------------------------------------------------------------------------
def _med_hele_saesonen(kh: pd.DataFrame) -> pd.DataFrame:
    """Dupliker rækkerne med fase_gruppe='hele_saesonen', så man kan vælge niveau med et filter."""
    return pd.concat([kh, kh.assign(fase_gruppe="hele_saesonen")], ignore_index=True)


NOEGLE = ["saeson", "fase_gruppe", "hold_id", "hold"]


def game_states(kh: pd.DataFrame) -> pd.DataFrame:
    """A) Minutter og procent foran / uafgjort / bagud."""
    g = (_med_hele_saesonen(kh).groupby(NOEGLE)
         .agg(kampe=("kamp_id", "count"), min_foran=("min_foran", "sum"),
              min_uafgjort=("min_uafgjort", "sum"), min_bagud=("min_bagud", "sum"))
         .reset_index())
    total = g[["min_foran", "min_uafgjort", "min_bagud"]].sum(axis=1)
    for s in ("foran", "uafgjort", "bagud"):
        g[f"pct_{s}"] = (100 * g[f"min_{s}"] / total).round(1)
    g["netto_pct"] = (g.pct_foran - g.pct_bagud).round(1)  # foran minus bagud: én samlet målestok
    return g


def alternativ_tabel(kh: pd.DataFrame) -> pd.DataFrame:
    """
    B) Point hvis kampene var stoppet efter 15/30/45/60/75 min, og den rigtige stilling (90).
       Placering pr. stoptidspunkt + 'sene_point' = point(90) − point(75).
       Placering: point, så målforskel, så scorede mål (forenklet; ikke DBU's fulde regler).
    """
    d = _med_hele_saesonen(kh)
    pointkol = [f"point_{t}" for t in STOP_MINUTTER] + ["point"]
    t = (d.groupby(NOEGLE)
         .agg(kampe=("kamp_id", "count"), maal_for=("maal_for", "sum"), maal_imod=("maal_imod", "sum"),
              **{k: (k, "sum") for k in pointkol})
         .reset_index().rename(columns={"point": "point_90"}))
    t["maalforskel"] = t.maal_for - t.maal_imod

    # Slutspilsgruppe: i den rigtige tabel står mesterskabsgruppen altid over nedrykningsgruppen.
    gruppe = (kh[kh.fase_gruppe == "slutspil"].groupby(["saeson", "hold_id"]).fase.first()
              .map({"mesterskabsspil": 0, "nedrykningsspil": 1}).rename("_gruppe").reset_index())
    t = t.merge(gruppe, on=["saeson", "hold_id"], how="left")
    t["_gruppe"] = np.where(t.fase_gruppe == "grundspil", 0, t["_gruppe"].fillna(0))

    for m in STOP_MINUTTER + [90]:
        # Rangordning inden for samme sæson og fase-gruppe. Ved stoptidspunkter bruges kun point
        # (en simpel "hvad nu hvis"-tabel), ved 90 min også målforskel og scorede mål.
        noegle = [f"point_{m}", "maalforskel", "maal_for"] if m == 90 else [f"point_{m}"]
        orden = t.assign(_neg=-t._gruppe).sort_values(["_neg"] + noegle, ascending=False)
        t[f"plac_{m}"] = orden.groupby(["saeson", "fase_gruppe"]).cumcount() + 1
    t = t.drop(columns="_gruppe")
    t["sene_point"] = t.point_90 - t.point_75          # +: henter point i de sidste 15 min
    t["anden_halvleg_point"] = t.point_90 - t.point_45  # +: bedre efter pausen end ved pausen
    return t


def scoringstidspunkter(kh: pd.DataFrame) -> pd.DataFrame:
    """C) Mål for og imod pr. 15-minutters interval (lang form: én række pr. interval)."""
    d = _med_hele_saesonen(kh)
    kol = [f"{r}_{n}" for n, _, _ in INTERVALLER for r in ("for", "imod")]
    s = d.groupby(NOEGLE)[kol].sum().reset_index()
    lang = []
    for navn, _, _ in INTERVALLER:
        lang.append(s[NOEGLE].assign(interval=navn, maal_for=s[f"for_{navn}"], maal_imod=s[f"imod_{navn}"]))
    return pd.concat(lang, ignore_index=True)


def comebacks(kh: pd.DataFrame) -> pd.DataFrame:
    """
    D) Point fra bagud-positioner, point tabt fra foran-positioner, og point når holdet scorer først.
       'point_hentet' = point i kampe, hvor holdet på et tidspunkt var bagud.
       'point_tabt'   = 3 − point i kampe, hvor holdet på et tidspunkt var foran.
    """
    d = _med_hele_saesonen(kh)
    d = d.assign(
        hentet=np.where(d.var_bagud, d.point, 0),
        tabt=np.where(d.var_foran, 3 - d.point, 0),
        p_scorede_foerst=np.where(d.scorede_foerst, d.point, 0),
        p_modstander_foerst=np.where(d.modstander_scorede_foerst, d.point, 0),
    )
    c = (d.groupby(NOEGLE)
         .agg(kampe=("kamp_id", "count"),
              kampe_bagud=("var_bagud", "sum"), point_hentet=("hentet", "sum"),
              kampe_foran=("var_foran", "sum"), point_tabt=("tabt", "sum"),
              scorede_foerst=("scorede_foerst", "sum"), point_scorede_foerst=("p_scorede_foerst", "sum"),
              modstander_foerst=("modstander_scorede_foerst", "sum"),
              point_modstander_foerst=("p_modstander_foerst", "sum"))
         .reset_index())
    # Point pr. kamp i de to situationer (NaN hvis situationen aldrig opstod)
    c["ppk_scorede_foerst"] = (c.point_scorede_foerst / c.scorede_foerst.replace(0, np.nan)).round(2)
    c["ppk_modstander_foerst"] = (c.point_modstander_foerst / c.modstander_foerst.replace(0, np.nan)).round(2)
    return c


def stilling(kh: pd.DataFrame, saeson: str, form_antal: int = 5) -> pd.DataFrame:
    """
    Den aktuelle stilling for én sæson (hele sæsonen), til forsidens overblik:
    placering, kampe, V/U/T, mål, målforskel, point, form (seneste kampe) og andel af tiden
    foran / uafgjort / bagud.
    """
    d = kh[kh.saeson == saeson].sort_values("kickoff_utc")
    tabel = alternativ_tabel(d)
    tabel = tabel[tabel.fase_gruppe == "hele_saesonen"].copy()
    gs = game_states(d)
    gs = gs[gs.fase_gruppe == "hele_saesonen"][["hold_id", "pct_foran", "pct_uafgjort", "pct_bagud"]]

    res = d.assign(r=np.select([d.point == 3, d.point == 1], ["V", "U"], "T"))
    vut = res.groupby("hold_id").r.value_counts().unstack(fill_value=0).reindex(columns=["V", "U", "T"], fill_value=0)
    form = res.groupby("hold_id").r.apply(lambda s: "".join(s.tail(form_antal))).rename("form")

    ud = (tabel.merge(gs, on="hold_id").merge(vut, left_on="hold_id", right_index=True)
          .merge(form, left_on="hold_id", right_index=True))
    kol = ["plac_90", "hold_id", "hold", "kampe", "V", "U", "T", "maal_for", "maal_imod", "maalforskel",
           "point_90", "form", "pct_foran", "pct_uafgjort", "pct_bagud"]
    return ud[kol].rename(columns={"plac_90": "plac", "point_90": "point"}).sort_values("plac")


# ---------------------------------------------------------------------------
# 5. Kør alt og gem
# ---------------------------------------------------------------------------
def main() -> None:
    kh = kamp_hold()
    fejl = kontroller(kh)
    print(f"Grundtabel: {len(kh)} rækker ({kh.kamp_id.nunique()} kampe)")
    print(f"Kontrol: {len(fejl)} rækker fejler" + ("" if fejl.empty else f"\n{fejl[['kamp_id','tjek']]}"))
    if not fejl.empty:
        raise SystemExit("ANALYSEKONTROL FEJLER: game states eller resultater stemmer ikke. Siden opdateres ikke.")

    tabeller = {
        "an_kamp_hold": kh,
        "an_game_states": game_states(kh),
        "an_alternativ_tabel": alternativ_tabel(kh),
        "an_scoringstidspunkter": scoringstidspunkter(kh),
        "an_comebacks": comebacks(kh),
    }
    with duckdb.connect(str(CLEAN / "superliga.duckdb")) as con:
        for navn, df in tabeller.items():
            df.to_parquet(CLEAN / f"{navn}.parquet", index=False)
            con.register("df", df)
            con.execute(f"CREATE OR REPLACE TABLE {navn} AS SELECT * FROM df")
            con.unregister("df")
            print(f"  {navn:<24} {len(df):>6} rækker")


if __name__ == "__main__":
    main()
