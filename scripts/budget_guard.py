"""
Budgetvagt: ALLE forespørgsler til API-Football, GOAL API og Sportmonks skal gå gennem denne fil.

Hvad den gør:
  1. Læser API-nøgler fra .env (de skrives aldrig ud).
  2. Slår op i cachen (data/raw) først. Findes svaret, bruges det, og der sendes ingen forespørgsel.
  3. Viser, før kørslen, hvor mange forespørgsler den vil bruge, og beder om lov.
  4. Tæller dagens forbrug pr. API i data/usage_log.jsonl og stopper, når der er
     SIKKERHEDSMARGIN (10) forespørgsler tilbage.
  5. Holder pause mellem forespørgsler, så minutgrænsen ikke rammes.
  6. Bruger API'ets egen "remaining"-header som facit, hvis den er lavere end vores tælling.
  7. Prøver aldrig igen automatisk. Fejler noget, stopper den og viser fejlen.

Brug (eksempel):
    from budget_guard import BudgetGuard
    guard = BudgetGuard("api_football")
    calls = [("/fixtures", {"league": 119, "season": 2025})]
    guard.confirm(calls)               # viser plan + spørger om lov
    data = guard.get("/fixtures", {"league": 119, "season": 2025})

Se dagens forbrug uden at sende noget:
    .venv/bin/python scripts/budget_guard.py
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

# --- Stier -------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
USAGE_LOG = PROJECT_ROOT / "data" / "usage_log.jsonl"

# --- Grænser -----------------------------------------------------------------
# Kilder (tjekket 2026-10-07):
#   API-Football gratis: 100 forespørgsler/dag (nulstilles kl. 00:00 UTC), 10 pr. minut.
#   GOAL API FREE: 1.000 forespørgsler/dag (goal-api.com/pricing).
#     Derudover et nødloft på 6.000/minut og 130/sekund pr. nøgle (dokumentationen).
#   Sportmonks gratis: 3.000 pr. time pr. entity. Vores eget loft: 200/dag.
SAFETY_MARGIN = 10  # stop når der kun er så mange tilbage

APIS = {
    "api_football": {
        "name": "API-Football",
        "base_url": "https://v3.football.api-sports.io",
        "env_var": "API_FOOTBALL_KEY",
        "daily_limit": 100,
        "seconds_between": 7,  # 10/min => mindst 6 s; vi bruger 7 for en sikkerheds skyld
        "remaining_header": "x-ratelimit-requests-remaining",
    },
    "goal": {
        "name": "GOAL API",
        # llms.txt og Superliga-dækningssiden bruger denne adresse (dokumentationen nævner også
        # api.goal-api.com/v1). Superligaen er liga 135.
        "base_url": "https://goal-api.com/api/v1",
        "env_var": "GOAL_API_KEY",
        "daily_limit": 1000,
        "seconds_between": 2,  # langt under deres loft; vi har ikke travlt
        "remaining_header": "x-ratelimit-remaining",
    },
    "sportmonks": {
        "name": "Sportmonks",
        # Gratisplan: 3.000 kald pr. time pr. entity (Fixture, League, Season, ...).
        # Vores eget loft er 200 pr. dag, så vi er meget langt fra deres grænse.
        "base_url": "https://api.sportmonks.com/v3/football",
        "env_var": "SPORTMONKS_API_KEY",
        "daily_limit": 200,
        # Din konto rapporterer 180 pr. time pr. entity (ikke 3.000). Vi tæller alle kald
        # under ét, så loftet gælder uanset entity.
        "hourly_limit": 180,
        "seconds_between": 2,
        # Deres "remaining" er pr. time, ikke pr. dag, så den kan ikke bruges som dagsfacit.
        # Den logges i stedet som remaining_hourly.
        "remaining_header": None,
        "hourly_header": "x-ratelimit-remaining",
    },
}


class BudgetStop(Exception):
    """Kastes når budgettet ikke tillader flere forespørgsler, eller der ikke er givet lov."""


class ApiError(Exception):
    """Kastes når en forespørgsel fejler. Vi prøver ikke igen."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _read_log() -> list[dict]:
    if not USAGE_LOG.exists():
        return []
    with USAGE_LOG.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _append_log(entry: dict) -> None:
    USAGE_LOG.parent.mkdir(parents=True, exist_ok=True)
    with USAGE_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def cache_path(api: str, endpoint: str, params: dict | None) -> Path:
    """Fast filnavn for et kald, så samme kald altid rammer samme cachefil."""
    params = params or {}
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", endpoint).strip("_") or "root"
    param_str = "&".join(f"{k}={params[k]}" for k in sorted(params))
    readable = re.sub(r"[^a-zA-Z0-9=&-]+", "_", param_str)[:80]
    digest = hashlib.sha1(f"{endpoint}?{param_str}".encode()).hexdigest()[:8]
    name = f"{slug}__{readable}__{digest}.json" if param_str else f"{slug}__{digest}.json"
    return RAW_DIR / api / name


class BudgetGuard:
    def __init__(self, api: str):
        if api not in APIS:
            raise ValueError(f"Ukendt API '{api}'. Vælg en af: {', '.join(APIS)}")
        self.api = api
        self.cfg = APIS[api]
        self.approved = 0  # hvor mange netværkskald brugeren har sagt ja til i denne kørsel

    # --- Optælling -------------------------------------------------------------
    def used_today(self) -> int:
        """Dagens forbrug (UTC-døgn): det højeste af vores egen tælling og API'ets facit."""
        today = _now().date().isoformat()
        entries = [e for e in _read_log() if e["api"] == self.api and e["time"][:10] == today]
        own_count = sum(1 for e in entries if e["type"] == "request")
        header_values = [e["remaining"] for e in entries
                         if e["type"] == "response" and e.get("remaining") is not None]
        if header_values:
            used_by_header = self.cfg["daily_limit"] - min(header_values)
            return max(own_count, used_by_header)
        return own_count

    def used_last_hour(self) -> int:
        now = _now()
        return sum(1 for e in _read_log()
                   if e["api"] == self.api and e["type"] == "request"
                   and (now - datetime.fromisoformat(e["time"])).total_seconds() < 3600)

    def remaining_today(self) -> int:
        return self.cfg["daily_limit"] - self.used_today()

    def usable_today(self) -> int:
        """Hvor mange vi må bruge, før sikkerhedsmarginen rammes."""
        return max(0, self.remaining_today() - SAFETY_MARGIN)

    # --- Plan og tilladelse ----------------------------------------------------
    def count_needed(self, calls: list[tuple]) -> int:
        """Tæl hvor mange kald der IKKE allerede ligger i cachen."""
        needed = 0
        for call in calls:
            endpoint, params = call[0], call[1]
            refresh = call[2] if len(call) > 2 else False
            if refresh or not cache_path(self.api, endpoint, params).exists():
                needed += 1
        return needed

    def confirm(self, calls: list[tuple], assume_yes: bool = False) -> int:
        """
        Vis hvor mange forespørgsler kørslen vil bruge, og spørg om lov.
        calls: liste af (endpoint, params) eller (endpoint, params, refresh).
        """
        needed = self.count_needed(calls)
        name = self.cfg["name"]
        print(f"\n=== Budgetplan for {name} ===")
        print(f"Kald i alt:              {len(calls)}")
        print(f"Allerede i cache:        {len(calls) - needed}")
        print(f"Nye forespørgsler:       {needed}")
        print(f"Brugt i dag (UTC):       {self.used_today()} af {self.cfg['daily_limit']}")
        print(f"Må bruges før margin:    {self.usable_today()} (margin = {SAFETY_MARGIN})")

        if needed == 0:
            print("Alt ligger i cachen. Der sendes ingen forespørgsler.")
            return 0
        if needed > self.usable_today():
            raise BudgetStop(
                f"STOP: Kørslen kræver {needed} forespørgsler, men der må kun bruges "
                f"{self.usable_today()} mere i dag. Prøv igen i morgen eller hent færre ad gangen."
            )
        if not assume_yes:
            answer = input(f"Vil du bruge {needed} forespørgsler på {name}? Skriv 'ja': ").strip().lower()
            if answer not in ("ja", "j", "yes", "y"):
                raise BudgetStop("Afbrudt. Ingen forespørgsler sendt.")
        self.approved += needed
        return needed

    # --- Selve forespørgslen ---------------------------------------------------
    def get(self, endpoint: str, params: dict | None = None, refresh: bool = False):
        """
        Hent et endpoint. Bruger cachen, hvis svaret findes (medmindre refresh=True).
        Færdigspillede kampe skal derfor aldrig hentes med refresh=True.
        """
        path = cache_path(self.api, endpoint, params)
        if path.exists() and not refresh:
            return json.loads(path.read_text(encoding="utf-8"))

        # 1) Er der givet lov?
        if self.approved <= 0:
            raise BudgetStop(
                "STOP: Forespørgslen er ikke godkendt. Kald guard.confirm(...) først."
            )
        # 2) Er der budget?
        if self.remaining_today() <= SAFETY_MARGIN:
            raise BudgetStop(
                f"STOP: Kun {self.remaining_today()} forespørgsler tilbage i dag på "
                f"{self.cfg['name']} (sikkerhedsmargin {SAFETY_MARGIN}). Fortsæt i morgen."
            )
        # 2b) Timeloft (kun API'er med et "hourly_limit")
        if self.cfg.get("hourly_limit") and self.used_last_hour() >= self.cfg["hourly_limit"] - SAFETY_MARGIN:
            raise BudgetStop(
                f"STOP: {self.used_last_hour()} forespørgsler til {self.cfg['name']} den seneste time "
                f"(loft {self.cfg['hourly_limit']}, margin {SAFETY_MARGIN}). Vent en time og kør igen."
            )
        # 3) Pause, så minutgrænsen ikke rammes
        self._wait_for_slot()

        # 4) Log FØR afsendelse, så kaldet tælles, selv hvis noget går galt undervejs
        _append_log({"time": _now().isoformat(), "api": self.api, "type": "request",
                     "endpoint": endpoint, "params": params or {}})
        self.approved -= 1

        key = self._key()
        if self.api == "api_football":
            headers = {"x-apisports-key": key}
        elif self.api == "sportmonks":
            headers = {"Authorization": key}  # nøglen i headeren, aldrig i URL'en
        else:
            # Dokumentationen siger Bearer, din note siger X-API-Key. Vi sender begge,
            # så et forkert headernavn ikke koster en ekstra forespørgsel.
            headers = {"Authorization": f"Bearer {key}", "X-API-Key": key}

        try:
            resp = requests.get(self.cfg["base_url"] + endpoint, params=params,
                                headers=headers, timeout=30)
        except requests.RequestException as e:
            raise ApiError(f"Netværksfejl mod {self.cfg['name']} {endpoint}: {type(e).__name__}") from None

        remaining = self._read_remaining_header(resp, self.cfg["remaining_header"])
        log_entry = {"time": _now().isoformat(), "api": self.api, "type": "response",
                     "endpoint": endpoint, "status": resp.status_code, "remaining": remaining}
        if self.cfg.get("hourly_header"):
            log_entry["remaining_hourly"] = self._read_remaining_header(resp, self.cfg["hourly_header"])
        _append_log(log_entry)

        if resp.status_code != 200:
            raise ApiError(f"{self.cfg['name']} svarede {resp.status_code} på {endpoint}:\n{resp.text[:800]}")
        try:
            data = resp.json()
        except ValueError:
            raise ApiError(f"Svaret fra {endpoint} var ikke JSON:\n{resp.text[:800]}") from None

        # API-Football svarer 200 men lægger fejl i "errors" (fx plan-begrænsning)
        errors = data.get("errors") if isinstance(data, dict) else None
        if errors:
            raise ApiError(f"{self.cfg['name']} returnerede fejl på {endpoint}: {errors}")
        if isinstance(data, dict) and data.get("success") is False:
            raise ApiError(f"{self.cfg['name']} returnerede fejl på {endpoint}: {data.get('error')}")

        # Kun gyldige svar caches
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        return data

    # --- Hjælpere --------------------------------------------------------------
    def _key(self) -> str:
        load_dotenv(PROJECT_ROOT / ".env")
        key = (os.getenv(self.cfg["env_var"]) or "").strip()  # strip fjerner mellemrum i .env
        if not key:
            raise BudgetStop(f"Mangler {self.cfg['env_var']} i .env")
        return key

    def _wait_for_slot(self) -> None:
        last = [e for e in _read_log() if e["api"] == self.api and e["type"] == "request"]
        if not last:
            return
        elapsed = (_now() - datetime.fromisoformat(last[-1]["time"])).total_seconds()
        wait = self.cfg["seconds_between"] - elapsed
        if wait > 0:
            time.sleep(wait)

    @staticmethod
    def _read_remaining_header(resp, header: str | None) -> int | None:
        if not header:
            return None
        value = resp.headers.get(header)
        try:
            return int(value) if value is not None else None
        except ValueError:
            return None


def print_status() -> None:
    print(f"Forbrug i dag ({_now().date()} UTC). Der sendes ingen forespørgsler.")
    for api in APIS:
        g = BudgetGuard(api)
        print(f"  {g.cfg['name']:<13} brugt {g.used_today():>4} af {g.cfg['daily_limit']:<5} "
              f"| må bruge {g.usable_today()} mere i dag")


if __name__ == "__main__":
    try:
        print_status()
    except BudgetStop as e:
        sys.exit(str(e))
