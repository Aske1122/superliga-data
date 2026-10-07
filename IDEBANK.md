# Idébank

Artikelidéer fundet i tallene (data til og med 20. september 2026).
Alle tal kommer fra tabellerne `an_*` i `data/clean/superliga.duckdb`. Kør `.venv/bin/python scripts/analyse.py` for at genberegne dem.

"Hele sæsonen" = grundspil + slutspil (32 kampe pr. hold). Playoff-kampe om Europa er ikke med.

---

## 1. Guldet, der forsvandt i de sidste 15 minutter (Brøndby 2023/24)
- **Spørgsmål:** Kostede sene mål Brøndby mesterskabet?
- **Tal:**
  - Med kampene stoppet efter 75 minutter havde Brøndby 70 point og var nummer 1. FCM havde 65 og var nummer 2.
  - Den rigtige slutstilling: FCM 63, Brøndby 62.
  - Brøndby tabte 27 point fra føring den sæson. Det er flest af alle hold i alle sæsoner siden 2020/21.
- **Graf:** Linjegraf over pointforskellen mellem de to hold med stop efter 15, 30, …, 90 minutter. Eller et hældningsdiagram: placering efter 75 minutter mod den rigtige placering.
- **Data:** Ja, alt findes (`an_alternativ_tabel`, `an_comebacks`).

## 2. Fordelen ved at score først bliver mindre
- **Spørgsmål:** Er det blevet mindre afgørende at score kampens første mål?
- **Tal:**
  - Point pr. kamp for holdet, der scorer først: 2,27 (2020/21) → 2,15 → 2,26 → 2,10 → 2,08 → 2,11 (2025/26).
  - Holdet, der kommer bagud først: 0,53 → 0,59 → 0,51 → 0,69 → 0,67 → 0,70.
  - Samtidig er antallet af mål steget fra 2,66–2,89 til 3,10–3,14 pr. kamp i 2024/25 og 2025/26.
- **Graf:** To linjer over sæsonerne ("scorede først" og "kom bagud først") med ligasnittet for mål pr. kamp som lille ekstragraf.
- **Data:** Ja. Det kan være en tendens eller tilfældig variation, så det bør testes, fx med et konfidensinterval pr. sæson.

## 3. Game states forklarer tabellen, men FCM slår modellen hvert år
- **Spørgsmål:** Hvem får flere eller færre point, end deres tid i front tilsiger?
- **Tal:**
  - "Netto tid foran" (procent foran minus procent bagud) og point pr. kamp hænger stærkt sammen i grundspillet: korrelation 0,91.
  - FCM får flere point end forventet i tre sæsoner: +0,50 point pr. kamp (2024/25), +0,42 (2023/24) og +0,40 (2020/21).
  - Mest uheldige: AaB 2022/23 (−0,39) og Vejle 2023/24 (−0,37).
- **Graf:** Punktdiagram med netto tid foran (x) og point pr. kamp (y). Regressionslinje i grå, FCM fremhævet med accentfarve.
- **Data:** Ja (`an_game_states` og `an_alternativ_tabel`).

## 4. Pausetabellen lyver
- **Spørgsmål:** Hvilke hold er bedst efter pausen?
- **Tal:**
  - Randers 2022/23 lå nummer 12 i grundspillet ved pausen (19 point), men endte nummer 5 (32 point).
  - Sønderjyske 2025/26: fra 9. til 3.-plads.
  - 2026/27: Silkeborg fra 3. til 7.-plads (se artikeludkastet).
- **Graf:** Hældningsdiagram for én sæson, eller små diagrammer for alle sæsoner, hvor de største bevægelser fremhæves.
- **Data:** Ja.

## 5. Sene kollapser: OB 2023/24
- **Spørgsmål:** Hvem vinder og taber flest point efter det 75. minut?
- **Tal:**
  - OB 2023/24: nummer 7 efter 75 minutter, nummer 11 i virkeligheden (42 → 32 point, altså −10 sene point). Holdet rykkede ned.
  - Viborg 2023/24: +11 sene point (fra 11. til 8.-plads).
  - FCM 2024/25: +10 sene point.
- **Graf:** Søjlediagram med sene point pr. hold (point efter 90 minutter minus point efter 75), sorteret og opdelt i plus og minus, med OB fremhævet.
- **Data:** Ja.

## 6. Det sidste kvarter er det mest målrige
- **Spørgsmål:** Hvornår falder målene, og har det ændret sig?
- **Tal:**
  - Minut 76–90+ står for 20–24 % af målene i hver sæson. Det er den største andel af alle intervaller.
  - Minut 0–15 står kun for 13–16 %.
  - 8–10 % af alle mål falder i tillægstid.
- **Graf:** Varmekort med intervaller (x), sæsoner (y) og andel af mål (farve). Eller søjler for intervallerne med alle sæsoner samlet.
- **Data:** Delvist. Intervallet 76–90+ indeholder tillægstid, så det er længere end 15 minutter. Mål pr. minut kræver den faktiske tillægstid, som vi ikke har.

## 7. Udskiftningerne kommer tidligere
- **Spørgsmål:** Bruger trænerne bænken tidligere og mere?
- **Tal:**
  - Gennemsnitligt udskiftningsminut: 70,9 (2020/21) → 70,0 (2025/26) → 67,8 (2026/27 indtil nu).
  - Udskiftninger pr. kamp (begge hold): 8,46 → 9,34 → 9,50.
- **Graf:** Linjegraf pr. sæson. Eller fordelingen af udskiftningsminutter pr. sæson (ridgeline eller histogram).
- **Data:** Ja (`udskiftninger`). Kunne udbygges med, hvordan stillingen var ved udskiftningen, altså om hold skifter mere, når de er bagud. Det kan vi beregne med de data, vi har.

## 8. Færre gule kort
- **Spørgsmål:** Er Superligaen blevet mindre kortglad, og hvorfor?
- **Tal:**
  - Gule kort pr. kamp: 4,11 (2020/21) → 3,88 → 3,80 → 3,82 → 3,43 → 3,46 → 3,69 (2026/27 indtil nu).
- **Graf:** Linjegraf pr. sæson. Eventuelt kort pr. hold.
- **Data:** Delvist. Kortene har vi, men dommerdata mangler. Sportmonks kan levere dommere (`referees`), men det kræver nye forespørgsler, og det skal du godkende først.

## 9. Hjemmebanefordelen svinger
- **Spørgsmål:** Hvor meget er hjemmebanen værd, og hvilke hold er bedst hjemme?
- **Tal:**
  - Point pr. kamp hjemme mod ude: 1,59/1,16 (2020/21), 1,46/1,29 (2023/24, mindst forskel) og 1,64/1,08 (2024/25, størst forskel).
- **Graf:** "Håndvægtsdiagram" (prikker forbundet af en streg) for hjemme og ude pr. sæson. Eller pr. hold for en enkelt sæson.
- **Data:** Ja. Tilskuertal mangler, men kunne måske hentes via Sportmonks (kræver godkendelse).

## 10. Comeback-holdet AC Horsens (2026/27, til opfølgning)
- **Spørgsmål:** Hvordan kan et hold, der næsten altid er bagud, ligge midt i tabellen?
- **Tal:**
  - Horsens har været bagud i 8 af 9 kampe og 44 % af spilletiden. Det er mest i ligaen.
  - Alligevel har holdet hentet 8 point fra bagud og ligger nummer 6 med 11 point.
- **Graf:** "Tidslinje" pr. kamp: en vandret bjælke pr. kamp, farvet efter stillingen minut for minut (foran/uafgjort/bagud).
- **Data:** Ja. Den kan opdateres løbende, når nye runder hentes.
