"""
Henter Superliga-kampe + hændelser fra API-Football for sæsonerne 2022/23–2024/25.

Sådan virker det:
  1. Kampprogrammet hentes én gang pr. sæson (1 forespørgsel pr. sæson).
  2. Færdigspillede kampe hentes i bundter af 20 via /fixtures?ids=... (1 forespørgsel pr. 20 kampe).
     Svaret indeholder hændelser, opstillinger og statistik.
  3. Hver kamp gemmes som data/raw/api_football/kampe/<id>.json.
     Ligger filen der, hentes kampen ALDRIG igen.
  4. Er der ikke budget nok i dag, hentes så meget som muligt. Kør scriptet igen i morgen
     for at hente resten.

Brug:
    .venv/bin/python scripts/hent_api_football.py --plan     # vis kun planen, send intet
    .venv/bin/python scripts/hent_api_football.py            # hent (spørger om lov)
    .venv/bin/python scripts/hent_api_football.py --maks 1   # hent højst 1 bundt kampe
"""

import argparse
import json
import sys

from budget_guard import RAW_DIR, ApiError, BudgetGuard, BudgetStop, cache_path

LEAGUE = 119
SEASONS = [2022, 2023, 2024]
FINISHED = {"FT", "AET", "PEN"}  # slutfløjt, efter forlænget spilletid, efter straffespark
BATCH_SIZE = 20                  # API-Footballs maksimum for ids-parameteren
MATCH_DIR = RAW_DIR / "api_football" / "kampe"


def season_call(season: int) -> tuple:
    return ("/fixtures", {"league": LEAGUE, "season": season})


def finished_ids_without_file(guard: BudgetGuard) -> tuple[list[int], list[int]]:
    """Find færdigspillede kampe, der mangler. Returnerer (mangler, sæsoner uden program)."""
    missing, seasons_missing = [], []
    for season in SEASONS:
        endpoint, params = season_call(season)
        path = cache_path("api_football", endpoint, params)
        if not path.exists():
            seasons_missing.append(season)
            continue
        fixtures = json.loads(path.read_text(encoding="utf-8"))["response"]
        for fx in fixtures:
            fid = fx["fixture"]["id"]
            if fx["fixture"]["status"]["short"] in FINISHED and not (MATCH_DIR / f"{fid}.json").exists():
                missing.append(fid)
    return sorted(missing), seasons_missing


def batches(ids: list[int]) -> list[tuple]:
    chunks = [ids[i:i + BATCH_SIZE] for i in range(0, len(ids), BATCH_SIZE)]
    return [("/fixtures", {"ids": "-".join(map(str, c))}) for c in chunks]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", action="store_true", help="vis kun planen")
    parser.add_argument("--maks", type=int, default=None, help="højst så mange kampbundter i denne kørsel")
    parser.add_argument("--ja", action="store_true", help="du har allerede sagt ja")
    args = parser.parse_args()

    guard = BudgetGuard("api_football")
    missing, seasons_missing = finished_ids_without_file(guard)

    if args.plan:
        print(f"Sæsoner uden kampprogram: {seasons_missing or 'ingen'} -> {len(seasons_missing)} forespørgsler")
        print(f"Kendte færdigspillede kampe uden data: {len(missing)} -> {len(batches(missing))} forespørgsler")
        if seasons_missing:
            print(f"  + ca. 10 forespørgsler pr. manglende sæson ({len(seasons_missing) * 10}) når programmet er hentet")
        print(f"Må bruges i dag: {guard.usable_today()}")
        return

    # Trin 1: kampprogrammer
    if seasons_missing:
        calls = [season_call(s) for s in seasons_missing]
        guard.confirm(calls, assume_yes=args.ja)
        for endpoint, params in calls:
            n = len(guard.get(endpoint, params)["response"])
            print(f"  Sæson {params['season']}: {n} kampe i programmet")
        missing, _ = finished_ids_without_file(guard)

    # Trin 2: kampe med hændelser, i bundter af 20
    calls = batches(missing)
    if not calls:
        print("Alle færdigspillede kampe er allerede hentet. Ingen forespørgsler sendt.")
        return
    limit = min(len(calls), guard.usable_today(), args.maks or len(calls))
    if limit < len(calls):
        print(f"\nDer mangler {len(calls)} bundter. Denne kørsel henter {limit}; resten tages næste gang.")
    calls = calls[:limit]
    if not calls:
        sys.exit("Intet budget tilbage i dag. Kør igen i morgen.")
    guard.confirm(calls, assume_yes=args.ja)

    MATCH_DIR.mkdir(parents=True, exist_ok=True)
    for endpoint, params in calls:
        data = guard.get(endpoint, params)
        wanted = set(params["ids"].split("-"))
        got = set()
        for match in data["response"]:
            fid = str(match["fixture"]["id"])
            got.add(fid)
            (MATCH_DIR / f"{fid}.json").write_text(json.dumps(match, ensure_ascii=False), encoding="utf-8")
        if wanted - got:
            print(f"  ADVARSEL: API'et returnerede ikke kampene {sorted(wanted - got)}")
        print(f"  Gemt {len(got)} kampe")

    left, _ = finished_ids_without_file(guard)
    print(f"\nFærdig. Mangler stadig {len(left)} kampe ({len(batches(left))} forespørgsler).")


if __name__ == "__main__":
    try:
        main()
    except (BudgetStop, ApiError) as e:
        sys.exit(f"\n{e}")
