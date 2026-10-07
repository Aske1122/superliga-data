"""
Henter Superliga-kampe + hændelser fra Sportmonks for sæsonerne 2020/21–2026/27.

Den billige vej:
  - Afsluttede sæsoner: ÉT kald pr. sæson. /seasons/{id} med indlejrede includes giver
    alle sæsonens kampe med hold, resultater og hændelser på én gang (includes pagineres ikke).
  - Igangværende sæson: ét kald for kampprogrammet (uden hændelser), og derefter
    /fixtures/multi/{ids} for op til 50 nyligt færdigspillede kampe pr. kald.
  - Hver færdigspillet kamp gemmes som data/raw/sportmonks/kampe/<id>.json
    og hentes ALDRIG igen.

Brug:
    .venv/bin/python scripts/hent_sportmonks.py --plan     # vis planen, send intet
    .venv/bin/python scripts/hent_sportmonks.py --maks 1   # højst 1 kald (fx en test)
    .venv/bin/python scripts/hent_sportmonks.py            # hent (spørger om lov)
"""

import argparse
import json
import sys

from budget_guard import RAW_DIR, ApiError, BudgetGuard, BudgetStop, cache_path

LEAGUE = 271
SEASONS = {  # navn -> Sportmonks season_id (fra /leagues/271?include=seasons)
    "2020/21": 17328, "2021/22": 18334, "2022/23": 19686, "2023/24": 21644,
    "2024/25": 23584, "2025/26": 25536, "2026/27": 27897,
}
CURRENT = "2026/27"
FINISHED_STATES = {5, 7, 8}  # FT, efter forlænget spilletid (AET), efter straffespark (FT_PEN)
FIXTURE_INCLUDES = "participants;scores;events.type"
SEASON_INCLUDES = "stages;" + ";".join(f"fixtures.{i}" for i in FIXTURE_INCLUDES.split(";"))
MULTI_MAX = 50
MATCH_DIR = RAW_DIR / "sportmonks" / "kampe"


def season_full_call(season_id: int) -> tuple:
    return (f"/seasons/{season_id}", {"include": SEASON_INCLUDES})


def schedule_call(season_id: int) -> tuple:
    return (f"/seasons/{season_id}", {"include": "stages;fixtures"}, True)  # True = hent frisk


def multi_calls(ids: list[int]) -> list[tuple]:
    chunks = [ids[i:i + MULTI_MAX] for i in range(0, len(ids), MULTI_MAX)]
    return [(f"/fixtures/multi/{','.join(map(str, c))}", {"include": FIXTURE_INCLUDES}) for c in chunks]


def save_finished(fixtures: list[dict], season_name: str, stages: dict) -> int:
    """Gem hver færdigspillet kamp som sin egen fil. Returnerer antal gemte."""
    MATCH_DIR.mkdir(parents=True, exist_ok=True)
    n = 0
    for fx in fixtures:
        if fx["state_id"] in FINISHED_STATES and fx.get("events") is not None:
            fx["_saeson"] = season_name
            fx["_fase"] = stages.get(fx.get("stage_id"))
            (MATCH_DIR / f"{fx['id']}.json").write_text(json.dumps(fx, ensure_ascii=False), encoding="utf-8")
            n += 1
    return n


def stage_names(season_data: dict) -> dict:
    return {s["id"]: s["name"] for s in season_data.get("stages") or []}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", action="store_true")
    parser.add_argument("--maks", type=int, default=None, help="højst så mange kald i denne kørsel")
    parser.add_argument("--ja", action="store_true", help="du har allerede sagt ja")
    args = parser.parse_args()
    guard = BudgetGuard("sportmonks")

    # Afsluttede sæsoner, hvis fulde sæsonsvar ikke ligger i cachen endnu
    old = [name for name in SEASONS if name != CURRENT
           and not cache_path("sportmonks", *season_full_call(SEASONS[name])).exists()]
    calls = [season_full_call(SEASONS[n]) for n in old]
    # Igangværende sæson: kampprogram (altid frisk) + multi-kald bagefter
    calls.append(schedule_call(SEASONS[CURRENT]))

    if args.plan:
        print(f"Afsluttede sæsoner der mangler: {old or 'ingen'} -> {len(old)} kald")
        print("Igangværende sæson: 1 kald (kampprogram) + 1 kald pr. 50 nye færdigspillede kampe")
        print(f"Brugt i dag: {guard.used_today()} af {guard.cfg['daily_limit']} | "
              f"seneste time: {guard.used_last_hour()} af {guard.cfg['hourly_limit']}")
        return

    if args.maks is not None:
        calls = calls[:args.maks]
    guard.confirm(calls, assume_yes=args.ja)
    budget_left = len(calls) if args.maks is None else args.maks

    for call in calls:
        endpoint, params = call[0], call[1]
        refresh = call[2] if len(call) > 2 else False
        name = next(n for n, sid in SEASONS.items() if endpoint == f"/seasons/{sid}")
        data = guard.get(endpoint, params, refresh=refresh)["data"]
        budget_left -= 1
        if name != CURRENT:
            n = save_finished(data["fixtures"], name, stage_names(data))
            print(f"  {name}: {len(data['fixtures'])} kampe i sæsonen, {n} færdigspillede gemt")
            continue

        # Igangværende sæson: find færdigspillede kampe vi ikke har
        stages = stage_names(data)
        missing = sorted(fx["id"] for fx in data["fixtures"]
                         if fx["state_id"] in FINISHED_STATES and not (MATCH_DIR / f"{fx['id']}.json").exists())
        mcalls = multi_calls(missing)
        if args.maks is not None:
            mcalls = mcalls[:max(0, budget_left)]
        print(f"  {name}: {len(missing)} nye færdigspillede kampe -> {len(mcalls)} kald")
        if mcalls:
            guard.confirm(mcalls, assume_yes=args.ja)
            for endpoint, params in mcalls:
                fixtures = guard.get(endpoint, params)["data"]
                print(f"    gemt {save_finished(fixtures, name, stages)} kampe")

    print(f"\nFærdig. Kampe i data/raw/sportmonks/kampe/: {len(list(MATCH_DIR.glob('*.json')))}")


if __name__ == "__main__":
    try:
        main()
    except (BudgetStop, ApiError) as e:
        sys.exit(f"\n{e}")
