"""
Fase 2: test af datakilderne med højst 5 forespørgsler pr. API.

Hvert trin er en lille kørsel, der viser sit forbrug og beder om lov (via budgetvagten):
    .venv/bin/python scripts/fase2_test.py af-overblik         # 2 kald: ligaens sæsoner + sæsonens kampe
    .venv/bin/python scripts/fase2_test.py af-saeson 2024      # 1 kald: kampe i en ældre sæson
    .venv/bin/python scripts/fase2_test.py af-kamp <fixture_id> # 1 kald: én kamp inkl. hændelser
    .venv/bin/python scripts/fase2_test.py goal-overblik       # 1 kald: ligaens kommende kampe
    .venv/bin/python scripts/fase2_test.py goal-resultater     # 1 kald: ligaens spillede kampe
    .venv/bin/python scripts/fase2_test.py goal-kamp <id>      # 2 kald: hændelser + udskiftninger

Tilføj --ja, hvis du allerede har sagt ja (så spørger scriptet ikke igen).
Svarene caches i data/raw, så en gentagen kørsel koster 0 forespørgsler.
"""

import sys

from budget_guard import ApiError, BudgetGuard, BudgetStop

AF_LEAGUE = 119     # Superligaen hos API-Football
AF_SEASON = 2026    # sæsonen 2026/27 (API-Football bruger startåret)
GOAL_LEAGUE = 135   # Superligaen hos GOAL API


def run(api: str, calls: list[tuple], assume_yes: bool) -> list:
    guard = BudgetGuard(api)
    guard.confirm(calls, assume_yes=assume_yes)
    return [guard.get(endpoint, params) for endpoint, params in calls]


def main(args: list[str]) -> None:
    assume_yes = "--ja" in args
    args = [a for a in args if a != "--ja"]
    if not args:
        sys.exit(__doc__)
    step = args[0]

    if step == "af-overblik":
        run("api_football", [("/leagues", {"id": AF_LEAGUE}),
                             ("/fixtures", {"league": AF_LEAGUE, "season": AF_SEASON})], assume_yes)
    elif step == "af-saeson":
        run("api_football", [("/fixtures", {"league": AF_LEAGUE, "season": int(args[1])})], assume_yes)
    elif step == "goal-resultater":
        run("goal", [(f"/leagues/{GOAL_LEAGUE}/results", None)], assume_yes)
    elif step == "goal-filter":
        params = {"leagueId": GOAL_LEAGUE, "status": "FINISHED", "from": "2026-07-01", "to": "2026-10-07"}
        run("goal", [("/fixtures", params)], assume_yes)
    elif step == "goal-events":
        run("goal", [(f"/fixtures/{args[1]}/events", None)], assume_yes)
    elif step == "af-kamp":
        run("api_football", [("/fixtures", {"id": int(args[1])})], assume_yes)
    elif step == "goal-overblik":
        run("goal", [(f"/leagues/{GOAL_LEAGUE}/fixtures", None)], assume_yes)
    elif step == "goal-kamp":
        fid = args[1]
        run("goal", [(f"/fixtures/{fid}/events", None),
                     (f"/fixtures/{fid}/substitutions", None)], assume_yes)
    else:
        sys.exit(f"Ukendt trin: {step}\n{__doc__}")
    print("Færdig. Svarene ligger i data/raw/.")


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except (BudgetStop, ApiError) as e:
        sys.exit(f"\n{e}")
