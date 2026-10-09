"""
Krydstjek af vores data (Sportmonks) mod API-Football for sæsonerne 2022/23–2024/25.

Trin 1 (0 API-kald): Resultater for ALLE kampe fra API-Footballs kampprogrammer i cachen:
         stillingen efter 90 minutter og ved pausen sammenlignes med vores.
Trin 2 (1 kald pr. kamp, via budgetvagten): Mål med minut og hold for et udvalg af kampe:
         de kampe, hvor vi har rettet kildefejl, plus et tilfældigt udvalg.

Kør:
    .venv/bin/python scripts/krydstjek.py                  # kun trin 1 (ingen kald)
    .venv/bin/python scripts/krydstjek.py --stikproeve 20  # + trin 2 (spørger om lov)

Resultatet gemmes i data/clean/krydstjek_*.csv (kun lokalt).
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyse  # noqa: E402
from budget_guard import ApiError, BudgetGuard, BudgetStop, cache_path  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SAESONER = {2022: "2022/23", 2023: "2023/24", 2024: "2024/25"}   # API-Football bruger startåret
FAERDIG = {"FT", "AET", "PEN"}


def holdnavne() -> dict[str, str]:
    t = pd.read_csv(ROOT / "scripts" / "holdnavne.csv")
    return dict(zip(t[t.kilde == "api_football"].kilde_navn, t[t.kilde == "api_football"].hold_id))


def af_kampe() -> pd.DataFrame:
    """API-Footballs kampe (fra cachen) i vores holdkoder."""
    navne, rows, ukendte = holdnavne(), [], set()
    for aar, saeson in SAESONER.items():
        sti = cache_path("api_football", "/fixtures", {"league": 119, "season": aar})
        for f in json.loads(sti.read_text(encoding="utf-8"))["response"]:
            if f["fixture"]["status"]["short"] not in FAERDIG:
                continue
            h, u = f["teams"]["home"]["name"], f["teams"]["away"]["name"]
            ukendte |= {n for n in (h, u) if n not in navne}
            rows.append({"af_id": f["fixture"]["id"], "saeson": saeson,
                         "dato": f["fixture"]["date"][:10], "hjemme_id": navne.get(h, h), "ude_id": navne.get(u, u),
                         "af_ft_h": f["score"]["fulltime"]["home"], "af_ft_u": f["score"]["fulltime"]["away"],
                         "af_ht_h": f["score"]["halftime"]["home"], "af_ht_u": f["score"]["halftime"]["away"]})
    if ukendte:
        sys.exit(f"Holdnavne mangler i holdnavne.csv: {sorted(ukendte)}")
    return pd.DataFrame(rows)


def vores_kampe() -> pd.DataFrame:
    k = analyse.laes_kampe().query("saeson in @SAESONER.values()").copy()
    maal = analyse.laes_maal()
    ht = (maal[maal.periode == 1].groupby(["kamp_id", "side"]).size().unstack(fill_value=0)
          .reindex(columns=["hjemme", "ude"], fill_value=0).rename(columns={"hjemme": "ht_h", "ude": "ht_u"}))
    k = k.merge(ht, left_on="kamp_id", right_index=True, how="left").fillna({"ht_h": 0, "ht_u": 0})
    k["dato"] = k.kickoff_utc.dt.strftime("%Y-%m-%d")
    return k


def match(af: pd.DataFrame, vi: pd.DataFrame) -> pd.DataFrame:
    """Kobl kampene på sæson + hjemmehold + udehold (+ dato, hvis holdene mødes flere gange)."""
    m = vi.merge(af, on=["saeson", "hjemme_id", "ude_id"], how="outer", indicator=True, suffixes=("", "_af"))
    # Holdene kan mødes 2–3 gange hjemme i samme sæson (grundspil + slutspil): kræv samme dato ±1 dag
    begge = m[m._merge == "both"].copy()
    dag = (pd.to_datetime(begge.dato) - pd.to_datetime(begge.dato_af)).dt.days.abs()
    begge = begge[dag <= 1]
    return begge, m[m._merge != "both"]


def trin1() -> pd.DataFrame:
    af, vi = af_kampe(), vores_kampe()
    m, uparret = match(af, vi)
    m["ft_afviger"] = (m.hjemme_maal_90 != m.af_ft_h) | (m.ude_maal_90 != m.af_ft_u)
    m["ht_afviger"] = (m.ht_h != m.af_ht_h) | (m.ht_u != m.af_ht_u)
    print(f"\n=== Trin 1: resultater (0 API-kald) ===")
    kun_af = af[~af.af_id.isin(m.af_id)]
    kun_os = vi[~vi.kamp_id.isin(m.kamp_id)]
    print(f"Ligakampe hos os: {len(vi)} | kampe hos API-Football: {len(af)} | parret: {len(m)}")
    print(f"Kun hos os: {len(kun_os)} | kun hos API-Football: {len(kun_af)} "
          "(vores ligatal er uden playoff-kampe om Europa)")
    if len(kun_af):
        print(kun_af[["saeson", "dato", "hjemme_id", "ude_id", "af_ft_h", "af_ft_u"]].to_string(index=False))
    print(f"Slutresultat efter 90 min afviger: {int(m.ft_afviger.sum())} | pausestilling afviger: {int(m.ht_afviger.sum())}")
    afv = m[m.ft_afviger | m.ht_afviger]
    if len(afv):
        print(afv[["saeson", "dato", "hjemmehold", "udehold", "hjemme_maal_90", "ude_maal_90", "af_ft_h", "af_ft_u",
                   "ht_h", "ht_u", "af_ht_h", "af_ht_u"]].to_string(index=False))
    m.to_csv(ROOT / "data" / "clean" / "krydstjek_resultater.csv", index=False)
    return m


def af_maal(fixture: dict, side_af_id: dict) -> list[tuple]:
    """API-Footballs mål: (periode-minut, side). Straffesparkskonkurrence og brændte straffe tælles ikke."""
    ud = []
    for e in fixture["events"]:
        if e["type"] != "Goal" or e["detail"] == "Missed Penalty" or (e.get("comments") or "") == "Penalty Shootout":
            continue
        ud.append((e["time"]["elapsed"], e["time"]["extra"] or 0, side_af_id[e["team"]["id"]], e["detail"]))
    return ud


def trin2(m: pd.DataFrame, antal: int, ja: bool) -> None:
    # Udvalg: kampe hvor vi har rettet holdet på et mål + tilfældige kampe (fast frø = samme udvalg hver gang)
    rettede = set(analyse.laes_maal().query("hold_rettet").kamp_id)
    udvalg = pd.concat([m[m.kamp_id.isin(rettede)],
                        m[~m.kamp_id.isin(rettede)].sample(antal, random_state=2026)])
    calls = [("/fixtures", {"id": int(i)}) for i in udvalg.af_id]
    guard = BudgetGuard("api_football")
    guard.confirm(calls, assume_yes=ja)
    vores = analyse.laes_maal()
    rows = []
    for r, (endpoint, params) in zip(udvalg.itertuples(), calls):
        f = guard.get(endpoint, params)["response"][0]
        side_af = {f["teams"]["home"]["id"]: "hjemme", f["teams"]["away"]["id"]: "ude"}
        af = af_maal(f, side_af)
        # Selvmål: API-Football angiver nogle gange scorerens hold i stedet for det hold, der får målet.
        # Vi prøver begge tolkninger og bruger den, der passer med API-Footballs eget slutresultat.
        modsat = {"hjemme": "ude", "ude": "hjemme"}
        tolkninger = [Counter((mi, s) for mi, _, s, _ in af),
                      Counter((mi, modsat[s] if d == "Own Goal" else s) for mi, _, s, d in af)]
        slut = (f["goals"]["home"], f["goals"]["away"])
        af_c = next((t for t in tolkninger
                     if (sum(n for (_, s), n in t.items() if s == "hjemme"),
                         sum(n for (_, s), n in t.items() if s == "ude")) == slut), tolkninger[0])
        vi = Counter((x.minut, x.side) for x in vores[(vores.kamp_id == r.kamp_id) & (vores.periode <= 4)].itertuples())
        ens = vi == af_c
        rows.append({"kamp": f"{r.hjemmehold}–{r.udehold}", "dato": r.dato, "rettet_hos_os": r.kamp_id in rettede,
                     "maal_os": sum(vi.values()), "maal_af": len(af), "minut_og_hold_ens": ens,
                     "kun_os": sorted((vi - af_c).elements()), "kun_af": sorted((af_c - vi).elements())})
    d = pd.DataFrame(rows)
    d.to_csv(ROOT / "data" / "clean" / "krydstjek_maal.csv", index=False)
    print(f"\n=== Trin 2: mål med minut og hold ({len(d)} kampe, {len(calls)} API-kald) ===")
    print(f"Ens: {int(d.minut_og_hold_ens.sum())} af {len(d)}")
    print(d.to_string(index=False))


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--stikproeve", type=int, default=0, help="antal tilfældige kampe til trin 2 (0 = spring over)")
    p.add_argument("--ja", action="store_true")
    a = p.parse_args()
    m = trin1()
    if a.stikproeve:
        trin2(m, a.stikproeve, a.ja)


if __name__ == "__main__":
    try:
        main()
    except (BudgetStop, ApiError) as e:
        sys.exit(f"\n{e}")
