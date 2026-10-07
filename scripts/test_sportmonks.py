"""
Test af Sportmonks (højst 5 forespørgsler). Hvert trin spørger om lov via budgetvagten.

    .venv/bin/python scripts/test_sportmonks.py liga               # 1 kald: Superligaen + alle sæsoner
    .venv/bin/python scripts/test_sportmonks.py saeson <season_id> # 1 kald: en sæsons kampe
    .venv/bin/python scripts/test_sportmonks.py kamp <fixture_id>  # 1 kald: én kamp med hændelser

Tilføj --ja, hvis du allerede har sagt ja.
"""

import sys

from budget_guard import ApiError, BudgetGuard, BudgetStop

LEAGUE = 271  # Superligaen hos Sportmonks


def run(calls: list[tuple], assume_yes: bool) -> list:
    guard = BudgetGuard("sportmonks")
    guard.confirm(calls, assume_yes=assume_yes)
    results = [guard.get(endpoint, params) for endpoint, params in calls]
    for r in results:
        # Sportmonks svarer 200 med en "message" og uden "data", når planen ikke dækker det ønskede
        if "data" not in r:
            raise ApiError(f"Sportmonks gav intet data: {r.get('message')}")
    return results


def main(args: list[str]) -> None:
    assume_yes = "--ja" in args
    args = [a for a in args if a != "--ja"]
    if not args:
        sys.exit(__doc__)
    step = args[0]
    if step == "liga":
        run([(f"/leagues/{LEAGUE}", {"include": "seasons"})], assume_yes)
    elif step == "saeson":
        run([(f"/seasons/{args[1]}", {"include": "fixtures"})], assume_yes)
    elif step == "kamp":
        run([(f"/fixtures/{args[1]}", {"include": "events.type;participants;scores;state"})], assume_yes)
    else:
        sys.exit(f"Ukendt trin: {step}\n{__doc__}")
    print("Færdig. Svarene ligger i data/raw/sportmonks/.")


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except (BudgetStop, ApiError) as e:
        sys.exit(f"\n{e}")
