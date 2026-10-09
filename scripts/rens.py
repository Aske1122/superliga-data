"""
Rensning: rådata (data/raw) -> vores eget, kildeuafhængige format (data/clean).

Tabeller (se README/forklaring):
    kampe          én række pr. kamp
    maal           én række pr. mål
    kort           én række pr. kort
    udskiftninger  én række pr. udskiftning

Hver kilde har sin egen "oversætter"-funktion (fra_sportmonks). Analyserne bruger kun
de rensede tabeller, så en ny kilde kræver kun en ny oversætter.

Kør:  .venv/bin/python scripts/rens.py      (sender ingen forespørgsler)
"""

import csv
import json
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
CLEAN = ROOT / "data" / "clean"
HOLDNAVNE = Path(__file__).resolve().parent / "holdnavne.csv"

FASER = {
    "Regular Season": "grundspil",
    "Championship Round": "mesterskabsspil",
    "Relegation Round": "nedrykningsspil",
}
AFGJORT = {5: "ordinaer", 7: "forlaenget", 8: "straffespark"}
KORT = {"YELLOWCARD": "gult", "YELLOWREDCARD": "andet_gule", "REDCARD": "roedt"}
MAALTYPER = {"GOAL": "spil", "PENALTY": "straffe", "OWNGOAL": "selvmaal"}


def laes_holdnavne() -> dict:
    with HOLDNAVNE.open(encoding="utf-8") as f:
        return {(r["kilde"], r["kilde_navn"]): (r["hold_id"], r["hold"]) for r in csv.DictReader(f)}


def periode(minut: int) -> int:
    """1. halvleg, 2. halvleg, 1. og 2. forlængede halvleg. Tillægstid hører til perioden før."""
    if minut <= 45:
        return 1
    if minut <= 90:
        return 2
    if minut <= 105:
        return 3
    return 4


def stilling(result: str | None) -> tuple[int, int] | None:
    try:
        h, u = result.split("-")
        return int(h), int(u)
    except (AttributeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Oversætter: Sportmonks -> vores format
# ---------------------------------------------------------------------------
def fra_sportmonks(holdnavne: dict) -> dict[str, list[dict]]:
    kampe, maal, kort, skift = [], [], [], []
    ukendte_hold = set()

    for path in sorted((RAW / "sportmonks" / "kampe").glob("*.json")):
        fx = json.loads(path.read_text(encoding="utf-8"))
        kamp_id = f"sportmonks:{fx['id']}"

        # Hold: Sportmonks-id -> (side, vores hold_id, vores holdnavn)
        hold = {}
        for p in fx["participants"]:
            key = ("sportmonks", p["name"])
            if key not in holdnavne:
                ukendte_hold.add(p["name"])
            hid, navn = holdnavne.get(key, (p["name"], p["name"]))
            hold[p["id"]] = {"side": p["meta"]["location"], "hold_id": hid, "hold": navn}
        side_til_hold = {h["side"]: h for h in hold.values()}

        # Resultat efter 90 min: "2ND_HALF" (stillingen ved slutfløjt i 2. halvleg).
        # "CURRENT" bruges ikke, for i kampe med forlænget spilletid er den ikke konsistent.
        # Mål i forlænget spilletid tælles fra hændelserne længere nede.
        score = {"CURRENT": {}, "2ND_HALF": {}, "PENALTY_SHOOTOUT": {}}
        for s in fx["scores"]:
            if s["description"] in score:
                score[s["description"]][s["score"]["participant"]] = s["score"]["goals"]
        slut90 = score["2ND_HALF"] or score["CURRENT"]
        h90, u90 = slut90.get("home", 0), slut90.get("away", 0)
        afgjort = AFGJORT.get(fx["state_id"], "ukendt")
        kampe.append({
            "kamp_id": kamp_id,
            "kilde": "sportmonks",
            "kilde_kamp_id": str(fx["id"]),
            "saeson": fx["_saeson"],
            "fase": FASER.get(fx["_fase"], "playoff"),
            "kilde_runde_id": fx.get("round_id"),
            "kickoff_utc": pd.Timestamp(fx["starting_at"], tz="UTC"),
            "hjemme_id": side_til_hold["home"]["hold_id"],
            "hjemmehold": side_til_hold["home"]["hold"],
            "ude_id": side_til_hold["away"]["hold_id"],
            "udehold": side_til_hold["away"]["hold"],
            "hjemme_maal_90": h90,
            "ude_maal_90": u90,
            "hjemme_maal": h90,  # + mål i forlænget spilletid, lægges til nedenfor
            "ude_maal": u90,
            "afgjort": afgjort,
            "straffe_hjemme": score["PENALTY_SHOOTOUT"].get("home"),
            "straffe_ude": score["PENALTY_SHOOTOUT"].get("away"),
        })

        events = sorted(fx["events"], key=lambda e: (e["minute"] or 0, e["extra_minute"] or 0,
                                                     e["sort_order"] or 0, e["id"]))
        forrige = (0, 0)
        for e in events:
            if e.get("rescinded"):
                continue  # annulleret hændelse
            typ = e["type"]["developer_name"]
            minut = e["minute"] or 0
            basis = {
                "kamp_id": kamp_id,
                "kilde": "sportmonks",
                "haendelse_id": str(e["id"]),
                "periode": periode(minut),
                "minut": minut,
                "tillaegsminut": e["extra_minute"] or 0,
            }
            h = hold.get(e["participant_id"])

            if typ in MAALTYPER:
                # Holdet udledes af den løbende stilling ("2-1"), fordi den er mest pålidelig.
                # Kildens eget hold-felt bruges kun, hvis stillingen mangler eller er tvetydig.
                ny = stilling(e.get("result"))
                if ny and ny[0] - forrige[0] == 1 and ny[1] == forrige[1]:
                    side = "home"
                elif ny and ny[1] - forrige[1] == 1 and ny[0] == forrige[0]:
                    side = "away"
                else:
                    side = h["side"]
                if ny:
                    forrige = ny
                rettet = side != h["side"]
                mh = side_til_hold[side]
                maal.append({**basis,
                             "side": "hjemme" if side == "home" else "ude",
                             "hold_id": mh["hold_id"], "hold": mh["hold"],
                             "spiller": e["player_name"],
                             "assist": e["related_player_name"] if typ != "OWNGOAL" else None,
                             "maaltype": MAALTYPER[typ],
                             "stilling_hjemme": forrige[0], "stilling_ude": forrige[1],
                             "hold_rettet": rettet})
                if periode(minut) >= 3:  # mål i forlænget spilletid
                    kampe[-1]["hjemme_maal" if side == "home" else "ude_maal"] += 1
            elif typ in KORT:
                kort.append({**basis,
                             "side": "hjemme" if h["side"] == "home" else "ude",
                             "hold_id": h["hold_id"], "hold": h["hold"],
                             "spiller": e["player_name"], "korttype": KORT[typ]})
            elif typ == "SUBSTITUTION":
                skift.append({**basis,
                              "side": "hjemme" if h["side"] == "home" else "ude",
                              "hold_id": h["hold_id"], "hold": h["hold"],
                              "spiller_ind": e["player_name"],      # Sportmonks: player = ind
                              "spiller_ud": e["related_player_name"],
                              "skadet": bool(e.get("injured"))})

    if ukendte_hold:
        print(f"ADVARSEL: hold uden række i holdnavne.csv: {sorted(ukendte_hold)}")
    return {"kampe": kampe, "maal": maal, "kort": kort, "udskiftninger": skift}


def tilfoej_runde(kampe: pd.DataFrame) -> pd.DataFrame:
    """
    Rundenummer pr. kamp (1, 2, 3 ...), som Superligaen tæller dem.
    Kildens runder sorteres efter deres første kampdato inden for hver fase, så en udsat kamp
    stadig hører til sin oprindelige runde. Slutspillets runder fortsætter efter grundspillet
    (fx 23–32), og playoff om Europa er runden efter.
    """
    kampe = kampe.copy()
    kampe["kilde_runde_id"] = kampe.kilde_runde_id.fillna(-1).astype(int)   # playoff har intet runde-ID i kilden
    start = kampe.groupby(["saeson", "fase", "kilde_runde_id"]).kickoff_utc.min().rename("start").reset_index()
    start["nr"] = start.groupby(["saeson", "fase"]).start.rank(method="dense").astype(int)
    grund = start[start.fase == "grundspil"].groupby("saeson").nr.max().rename("grund_runder")
    start = start.merge(grund, on="saeson", how="left")
    slut = start[start.fase.isin(["mesterskabsspil", "nedrykningsspil"])].groupby("saeson").nr.max().rename("slut_runder")
    start = start.merge(slut, on="saeson", how="left").fillna({"slut_runder": 0})
    start["runde"] = start.nr
    start.loc[start.fase.isin(["mesterskabsspil", "nedrykningsspil"]), "runde"] = start.nr + start.grund_runder
    start.loc[start.fase == "playoff", "runde"] = start.grund_runder + start.slut_runder + 1
    kampe = kampe.merge(start[["saeson", "fase", "kilde_runde_id", "runde"]], on=["saeson", "fase", "kilde_runde_id"])
    kampe["runde"] = kampe.runde.astype(int)
    return kampe


def main() -> None:
    holdnavne = laes_holdnavne()
    tabeller = fra_sportmonks(holdnavne)
    # Her kan senere tilføjes fx fra_api_football(holdnavne) og tabellerne lægges sammen.

    CLEAN.mkdir(parents=True, exist_ok=True)
    db_path = CLEAN / "superliga.duckdb"
    db_path.unlink(missing_ok=True)
    con = duckdb.connect(str(db_path))
    for navn, rows in tabeller.items():
        df = pd.DataFrame(rows)
        if navn == "kampe":
            df = tilfoej_runde(df)
            # Kontrol: ingen hold må spille to gange i samme runde
            dobbelt = (pd.concat([df[["saeson", "runde", "hjemme_id"]].rename(columns={"hjemme_id": "h"}),
                                  df[["saeson", "runde", "ude_id"]].rename(columns={"ude_id": "h"})])
                       .duplicated().sum())
            if dobbelt:
                print(f"ADVARSEL: {dobbelt} tilfælde, hvor et hold spiller to gange i samme runde")
        if navn == "kampe":  # heltal, der kan være tomme (kun kampe med straffesparkskonkurrence)
            df[["straffe_hjemme", "straffe_ude"]] = df[["straffe_hjemme", "straffe_ude"]].astype("Int64")
        df.to_parquet(CLEAN / f"{navn}.parquet", index=False)
        con.register("df", df)
        con.execute(f"CREATE TABLE {navn} AS SELECT * FROM df")
        con.unregister("df")
        print(f"{navn:<14} {len(df):>6} rækker -> data/clean/{navn}.parquet")
    con.close()
    print(f"Alle tabeller ligger også i {db_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
