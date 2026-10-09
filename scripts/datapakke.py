"""
Mandagens datapakke: 3–5 observationer fra seneste runde og sæsonen indtil nu, med tal og grafer.
Det er IDÉER til artikler, ikke artikler. Pakken gemmes kun lokalt i data/datapakker/ (aldrig i repoet).

Kør:
    .venv/bin/python scripts/datapakke.py            # lav pakken for seneste runde
    .venv/bin/python scripts/datapakke.py --aabn     # ... og åbn den i browseren

Hele mandagsrutinen (hent nye kampe, rens, tjek, analysér, lav og åbn pakken):
    ./mandag.sh

Sender ingen API-forespørgsler. Bruger kun data/clean.
"""

from __future__ import annotations

import argparse
import base64
import html
import subprocess
import sys
from datetime import date
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyse  # noqa: E402
import stil     # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
UD = ROOT / "data" / "datapakker"
KAMPE_PR_RUNDE = 6            # 12 hold = 6 kampe pr. runde (også i slutspillet: 3 + 3)


# ---------------------------------------------------------------------------
# Data: sæson, seneste runde og stillingen før/efter runden
# ---------------------------------------------------------------------------
def tabel(kh: pd.DataFrame) -> pd.DataFrame:
    """Simpel stilling: point, målforskel, scorede mål -> placering."""
    t = (kh.groupby(["hold_id", "hold"])
         .agg(kampe=("kamp_id", "count"), point=("point", "sum"),
              mf=("maal_for", "sum"), mi=("maal_imod", "sum")).reset_index())
    t["maalforskel"] = t.mf - t.mi
    t = t.sort_values(["point", "maalforskel", "mf"], ascending=False).reset_index(drop=True)
    t["plac"] = t.index + 1
    return t


def hent_data():
    kh_alle = analyse.kamp_hold()
    saeson = kh_alle.saeson.max()
    kh = kh_alle[kh_alle.saeson == saeson]
    kampe = analyse.laes_kampe().query("saeson == @saeson").sort_values("kickoff_utc")
    runde_kampe = kampe.tail(KAMPE_PR_RUNDE)
    runde_ids = set(runde_kampe.kamp_id)
    runde_nr = int(kh.groupby("hold_id").size().max())
    foer = tabel(kh[~kh.kamp_id.isin(runde_ids)])
    efter = tabel(kh)
    return kh_alle, kh, saeson, runde_nr, runde_kampe, runde_ids, foer, efter


# ---------------------------------------------------------------------------
# Grafer (husstil, bred version, gemmes som PNG i pakkens mappe)
# ---------------------------------------------------------------------------
def gem_graf(fig, mappe: Path, navn: str) -> Path:
    sti = mappe / f"{navn}.png"
    fig.savefig(sti, dpi=stil.DPI_DELING)
    plt.close(fig)
    return sti


def graf_tabelbevaegelser(foer, efter, runde_nr, mappe):
    m = foer[["hold_id", "hold", "plac"]].merge(efter[["hold_id", "plac", "point"]], on="hold_id",
                                                 suffixes=("_foer", "_efter"))
    m["flyt"] = m.plac_foer - m.plac_efter
    fig, ax = stil.figur(f"Tabellen før og efter runde {runde_nr}",
                         "Placering før runden (venstre) og efter (højre) · største bevægelser fremhævet",
                         venstre=0.22)
    fig.subplots_adjust(right=0.78)
    stoerst = set(m.reindex(m.flyt.abs().sort_values(ascending=False).index).head(2).hold_id)
    for r in m.itertuples():
        farve = (stil.FORAN if r.flyt > 0 else stil.BAGUD) if r.hold_id in stoerst and r.flyt else stil.GRAA
        tyk = 2.4 if r.hold_id in stoerst and r.flyt else 1.1
        ax.plot([0, 1], [r.plac_foer, r.plac_efter], color=farve, linewidth=tyk, marker="o", markersize=4)
        ax.text(-0.04, r.plac_foer, r.hold, ha="right", va="center", fontsize=8.5)
        ax.text(1.04, r.plac_efter, f"{r.plac_efter}. {r.hold} ({r.point})", ha="left", va="center", fontsize=8.5)
    ax.set_ylim(len(m) + 0.6, 0.4)
    ax.set_xlim(0, 1)
    ax.set_xticks([])
    ax.set_yticks([])
    return m, gem_graf(fig, mappe, "tabelbevaegelser")


def graf_forventet(kh_alle, saeson, mappe):
    """Point pr. kamp mod 'netto tid foran' (foran minus bagud). Grå = alle tidligere sæsoner."""
    gs = analyse.game_states(kh_alle)
    t = analyse.alternativ_tabel(kh_alle)
    d = gs.merge(t[["saeson", "fase_gruppe", "hold_id", "point_90", "kampe"]], on=["saeson", "fase_gruppe", "hold_id", "kampe"])
    d = d[d.fase_gruppe == "hele_saesonen"].assign(ppk=lambda x: x.point_90 / x.kampe)
    hist = d[d.saeson != saeson]
    b, a = np.polyfit(hist.netto_pct, hist.ppk, 1)          # simpel lineær sammenhæng
    nu = d[d.saeson == saeson].assign(forventet=lambda x: a + b * x.netto_pct)
    nu["afvigelse"] = nu.ppk - nu.forventet
    fig, ax = stil.figur("Point pr. kamp mod tid i front",
                         f"Grå: alle hold 2020/21–{hist.saeson.max()} · farvet: {saeson} · linje: historisk sammenhæng",
                         venstre=0.1)
    ax.scatter(hist.netto_pct, hist.ppk, s=14, color=stil.GRAA_LYS, zorder=1)
    xs = np.linspace(d.netto_pct.min(), d.netto_pct.max(), 50)
    ax.plot(xs, a + b * xs, color=stil.GRAA, linewidth=1, zorder=2)
    yderst = set(nu.reindex(nu.afvigelse.abs().sort_values(ascending=False).index).head(3).hold_id)
    for r in nu.itertuples():
        farve = stil.ACCENT if r.hold_id in yderst else stil.FORAN
        ax.scatter(r.netto_pct, r.ppk, s=30, color=farve, zorder=3)
        ax.annotate(r.hold_id, (r.netto_pct, r.ppk), xytext=(4, 3), textcoords="offset points",
                    fontsize=8, color=farve, fontweight="semibold" if r.hold_id in yderst else "normal")
    ax.set_xlabel("Procent af tiden foran minus procent bagud")
    ax.set_ylabel("Point pr. kamp")
    stil.gitter(ax, "both")
    return nu.sort_values("afvigelse"), gem_graf(fig, mappe, "point-mod-tid-i-front")


# ---------------------------------------------------------------------------
# Observationer
# ---------------------------------------------------------------------------
def obs_tabel(foer, efter, runde_nr, mappe):
    m, graf = graf_tabelbevaegelser(foer, efter, runde_nr, mappe)
    op = m.sort_values("flyt", ascending=False).iloc[0]
    ned = m.sort_values("flyt").iloc[0]
    top = efter.iloc[0]
    nr2 = efter.iloc[1]
    fakta = [f"{top.hold} fører med {top.point} point, {top.point - nr2.point} foran {nr2.hold}."]
    if op.flyt > 0:
        fakta.append(f"Største klatrer: {op.hold}, fra {op.plac_foer}. til {op.plac_efter}. plads.")
    if ned.flyt < 0:
        fakta.append(f"Største fald: {ned.hold}, fra {ned.plac_foer}. til {ned.plac_efter}. plads.")
    bund = efter.iloc[-1]
    fakta.append(f"Bunden: {bund.hold} med {bund.point} point. Afstand til top 6: "
                 f"{efter.iloc[5].point - efter.iloc[6].point} point mellem 6. og 7. plads.")
    return {"titel": "Tabellen efter runden", "fakta": fakta, "graf": graf, "vaegt": abs(op.flyt) + abs(ned.flyt)}


def obs_sene_maal(kh, runde_ids, runde_kampe):
    r = kh[kh.kamp_id.isin(runde_ids)]
    sent = r[r.point != r.point_75]                         # point ændret efter 75. minut
    comeback = r[r.var_bagud & (r.point > 0)]
    fakta = []
    for x in sent.itertuples():
        retning = "vandt" if x.point > x.point_75 else "mistede"
        fakta.append(f"{x.hold} {retning} {abs(x.point - x.point_75)} point efter 75. minut mod "
                     f"{stil.holdnavn(x.modstander_id)} (slut {x.maal_for}-{x.maal_imod}).")
    for x in comeback.itertuples():
        fakta.append(f"{x.hold} var bagud mod {stil.holdnavn(x.modstander_id)}, men fik {x.point} point "
                     f"({x.maal_for}-{x.maal_imod}).")
    maal = int((runde_kampe.hjemme_maal + runde_kampe.ude_maal).sum())
    fakta.append(f"Runden gav {maal} mål i {len(runde_kampe)} kampe "
                 f"({stil.tal(maal / len(runde_kampe), 2)} pr. kamp).")
    return {"titel": "Sene mål og comebacks i runden", "fakta": fakta, "graf": None,
            "vaegt": 2 * len(sent) + len(comeback)}


def obs_forventet(kh_alle, saeson, mappe):
    nu, graf = graf_forventet(kh_alle, saeson, mappe)
    over = nu.iloc[-1]
    under = nu.iloc[0]
    fakta = [
        f"{over.hold}: {stil.tal(over.ppk, 2)} point pr. kamp, men tiden i front svarer historisk til "
        f"{stil.tal(over.forventet, 2)} (+{stil.tal(over.afvigelse, 2)}).",
        f"{under.hold}: {stil.tal(under.ppk, 2)} point pr. kamp mod forventet {stil.tal(under.forventet, 2)} "
        f"({stil.tal(under.afvigelse, 2)}).",
        "Mulig vinkel: effektivitet eller held? Følg om afvigelsen holder over flere runder.",
    ]
    return {"titel": "Flere eller færre point end tiden i front tilsiger", "fakta": fakta, "graf": graf,
            "vaegt": abs(over.afvigelse) + abs(under.afvigelse)}


def obs_stimer(kh):
    """Aktuelle stimer: kampe i træk uden nederlag / uden sejr / sejre i træk."""
    rows = []
    for hold_id, g in kh.sort_values("kickoff_utc").groupby("hold_id"):
        p = list(g.point)[::-1]                       # nyeste først
        def stime(betingelse):
            n = 0
            for x in p:
                if not betingelse(x):
                    break
                n += 1
            return n
        rows.append({"hold": g.hold.iloc[0], "ubesejret": stime(lambda x: x > 0),
                     "uden_sejr": stime(lambda x: x < 3), "sejre": stime(lambda x: x == 3)})
    s = pd.DataFrame(rows)
    fakta = []
    for kol, tekst in [("sejre", "sejre i træk"), ("ubesejret", "kampe i træk uden nederlag"),
                       ("uden_sejr", "kampe i træk uden sejr")]:
        bedst = s[s[kol] == s[kol].max()]
        if s[kol].max() >= 3:
            fakta.append(f"{' og '.join(bedst.hold)}: {s[kol].max()} {tekst}.")
    return {"titel": "Aktuelle stimer", "fakta": fakta or ["Ingen stimer på 3+ kampe."], "graf": None,
            "vaegt": s[["sejre", "ubesejret", "uden_sejr"]].max().max() / 2}


def obs_foeringer(kh_alle, saeson):
    cb = analyse.comebacks(kh_alle).query("saeson == @saeson and fase_gruppe == 'hele_saesonen'")
    hist = analyse.comebacks(kh_alle).query("saeson != @saeson and fase_gruppe == 'hele_saesonen'")
    snit = (hist.point_tabt / hist.kampe).mean()
    tabt = cb.sort_values("point_tabt", ascending=False).iloc[0]
    hentet = cb.sort_values("point_hentet", ascending=False).iloc[0]
    fakta = [
        f"Flest point tabt fra føring: {tabt.hold} ({tabt.point_tabt} på {tabt.kampe} kampe; "
        f"historisk snit pr. hold er {stil.tal(snit * tabt.kampe, 1)}).",
        f"Flest point hentet fra bagud: {hentet.hold} ({hentet.point_hentet}).",
    ]
    return {"titel": "Føringer og comebacks i sæsonen", "fakta": fakta, "graf": None,
            "vaegt": tabt.point_tabt / max(snit * tabt.kampe, 0.1)}


# ---------------------------------------------------------------------------
# HTML-pakke
# ---------------------------------------------------------------------------
def billede_html(sti: Path) -> str:
    data = base64.b64encode(sti.read_bytes()).decode()
    return f'<img src="data:image/png;base64,{data}" alt="">'


def skriv_html(saeson, runde_nr, runde_kampe, observationer, mappe: Path) -> Path:
    res = "".join(f"<li>{html.escape(k.hjemmehold)}–{html.escape(k.udehold)} {k.hjemme_maal}-{k.ude_maal}</li>"
                  for k in runde_kampe.itertuples())
    blokke = []
    for i, o in enumerate(observationer, 1):
        fakta = "".join(f"<li>{html.escape(f)}</li>" for f in o["fakta"])
        graf = billede_html(o["graf"]) if o["graf"] else ""
        blokke.append(f"<section><h2>{i}. {html.escape(o['titel'])}</h2><ul>{fakta}</ul>{graf}</section>")
    side = f"""<!doctype html><html lang="da"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Datapakke · runde {runde_nr}</title>
<style>
  body {{ font-family: Inter, -apple-system, Helvetica, Arial, sans-serif; background: #FCFBF7; color: #1A1A1A;
         max-width: 820px; margin: 2.5rem auto; padding: 0 1.25rem; line-height: 1.6; }}
  h1 {{ font-size: 1.6rem; margin: 0; }} h2 {{ font-size: 1.15rem; margin: 2.5rem 0 0.5rem; }}
  .meta {{ color: #6E6B64; font-size: 0.9rem; }} img {{ width: 100%; height: auto; margin-top: 0.75rem; }}
  section {{ border-top: 1px solid #E7E4DC; }} ul {{ padding-left: 1.2rem; }}
</style></head><body>
<h1>Datapakke: Superligaen {saeson}, runde {runde_nr}</h1>
<p class="meta">Lavet {date.today():%d-%m-%Y}. Idéer til artikler, ikke færdige tekster. Kun til eget brug (data/).</p>
<h2>Rundens resultater</h2><ul>{res}</ul>
{''.join(blokke)}
</body></html>"""
    sti = mappe / "datapakke.html"
    sti.write_text(side, encoding="utf-8")
    return sti


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--aabn", action="store_true", help="åbn pakken i browseren bagefter")
    args = parser.parse_args()

    kh_alle, kh, saeson, runde_nr, runde_kampe, runde_ids, foer, efter = hent_data()
    mappe = UD / f"{saeson.replace('/', '-')}-runde-{runde_nr:02d}"
    mappe.mkdir(parents=True, exist_ok=True)

    kandidater = [
        obs_tabel(foer, efter, runde_nr, mappe),
        obs_sene_maal(kh, runde_ids, runde_kampe),
        obs_forventet(kh_alle, saeson, mappe),
        obs_foeringer(kh_alle, saeson),
        obs_stimer(kh),
    ]
    # Tabellen først (kontekst), derefter de øvrige efter "interessanthed" (vægt), højst 5 i alt
    observationer = [kandidater[0]] + sorted(kandidater[1:], key=lambda o: o["vaegt"], reverse=True)[:4]
    sti = skriv_html(saeson, runde_nr, runde_kampe, observationer, mappe)
    print(f"Datapakke: {sti.relative_to(ROOT)} ({len(observationer)} observationer)")
    if args.aabn:
        subprocess.run(["open", str(sti)], check=False)


if __name__ == "__main__":
    main()
