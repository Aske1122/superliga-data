# Godmorgen ☕

Status fra natten 7.–8. oktober 2026.
**Der er ikke sendt én eneste API-forespørgsel.** Alt er lavet på de data, der allerede lå i `data/clean`.
Intet er pushet til GitHub eller lagt online.

---

## 1. Hvad der er lavet

| Fase | Hvad | Hvor |
|---|---|---|
| 4 | Fase 3 er committet (efter tjek af `.env` og `data/`). | git: `4515a67` |
| 5 | Et **analysemodul**, som alle artikler kan importere. Det beregner game states (A), den alternative tabel (B), scoringstidspunkter (C) og comebacks/føringer (D) for alle sæsoner og hold, opdelt i grundspil, slutspil og hele sæsonen. Resultaterne gemmes som tabeller. | `scripts/analyse.py` → `data/clean/an_*.parquet` + `superliga.duckdb` |
| 6 | En **husstil** til grafer: lys baggrund, dansk rød accent, blå/grå/orange til foran/uafgjort/bagud, Avenir Next og en kildelinje nederst. Hver graf gemmes som SVG til siden og som PNG på 1200×675 pixels til X og LinkedIn. | `scripts/stil.py`, testside `stiltest.qmd` |
| 7 | **Hjemmesiden** har nyt tema i samme farver og skrift, en forside med pladsholder til din intro og artikeloversigt, en metodeside med stikord og en om-side med pladsholdere. Den er tjekket i mobilbredde: ingen vandret scroll, og graferne skalerer. | `_quarto.yml`, `styles.scss`, `index.qmd`, `metode.qmd`, `om.qmd` |
| 8 | Et **artikeludkast** med 3 grafer, arbejdstitel og 3 alternative titler, stikord under hver graf, pladsholdere til din tekst og en metodeboks. Artiklen er markeret som kladde. | `posts/2026-10-foeringer-der-forsvinder/` |
| 9 | En **idébank** med 10 artikelidéer, tal, grafforslag og en vurdering af, om vi har dataene. | `IDEBANK.md` |

**Kort forklaret:**
- `analyse.py` er "regnemaskinen".
  - Den laver først én række pr. hold pr. kamp (`an_kamp_hold`) med fx minutter foran og point, hvis kampen var stoppet efter 15, 30, … minutter.
  - Alle de andre tabeller er summer af den.
  - En artikel skriver bare `import analyse` og bruger de færdige tal.
- `stil.py` er "designmanualen" for grafer.
  - `stil.figur("Titel", "Undertitel")` giver en tom graf i husstilen.
  - `stil.gem(fig, "navn", mappe)` gemmer den i begge formater.

---

## 2. Valgt artikeludkast: "Silkeborgs forsvundne føringer" (analyse D + B)

**Hvorfor:** Det er den skarpeste kontrast i 2026/27, og den kan fortælles med tre enkle grafer:
- Silkeborg har tabt **12 point fra føring** på 9 kampe, flest i ligaen. Det er næstflest efter 9 kampe i nogen sæson siden 2020/21.
- **Ved pausen ville Silkeborg ligge nummer 3**, men i virkeligheden ligger holdet nummer 7.
- Holdet har ført ved pausen 5 gange, men kun vundet én af kampene. Ligasnittet er cirka 72 % sejre efter pauseføring.
- **FC København er det modsatte:** Holdet har ført i 8 kampe og vundet alle 8, og har hentet 9 point fra bagud.

Game states (A) var også en mulighed, men "FCK fører mest" er en mindre overraskende historie.

---

## 3. De mest interessante fund

1. **Brøndby ville være blevet mester i 2023/24, hvis kampene stoppede efter 75 minutter.** De havde 70 point mod FCM's 65 på det tidspunkt, men tabte guldet med ét point (62 mod 63). Brøndby tabte 27 point fra føring den sæson, mest af alle hold i alle sæsoner.
2. **Fordelen ved at score først er skrumpet.**
   - Holdet, der scorer først: 2,27 point pr. kamp (2020/21) → cirka 2,10 (2023/24–2025/26).
   - Holdet, der kommer bagud først: 0,53 → 0,70.
3. **Game states forklarer tabellen næsten fuldstændigt.** Korrelationen mellem "netto tid foran" og point pr. kamp er 0,91. Men **FCM henter systematisk flere point**, end deres tid i front forudsiger, i tre forskellige sæsoner.
4. **Silkeborg og FCK i 2026/27**, som beskrevet ovenfor.
5. **AC Horsens 2026/27** har været bagud i 8 af 9 kampe og 44 % af tiden, men ligger nummer 6. Holdet har hentet 8 point fra bagud, næstflest i ligaen.

Flere detaljer står i `IDEBANK.md`.

---

## 4. Valg, jeg har truffet på dine vegne

| Valg | Hvad jeg gjorde | Hvorfor / hvad du kan overveje |
|---|---|---|
| **Kampens længde** | Altid **90 minutter**. Mål i tillægstid lægges på periodens sidste minut, så 45+2 tæller som 45 og 90+4 som 90. | Vi kender kun hændelsernes minut, ikke hvor lang tillægstiden faktisk var. Hvis vi fx brugte "sidste hændelse" som kampens længde, ville kampe med mange sene skift se længere ud end andre. Med 90 minutter er alle kampe lige lange og kan sammenlignes. Ulempen er, at tiden efter et mål i 90+3 tæller som 0 minutter. |
| **Forlænget spilletid** | **Tælles ikke med** i nogen analyse. | Det sker kun i 3 playoff-kampe om Europa. De kampe er heller ikke en del af ligaen og er helt udeladt. |
| **Grundspil og slutspil** | Alle tabeller findes i tre udgaver: `grundspil`, `slutspil` og `hele_saesonen`. | Grundspillet er det mest fair at sammenligne, fordi alle møder alle. I den samlede tabel står mesterskabsgruppen altid over nedrykningsgruppen, ligesom i den officielle stilling. |
| **Placering ved pointlighed** | Point → målforskel → scorede mål. | Det er en forenkling af DBU's regler, hvor indbyrdes opgør mangler. Ved "stoppet efter X minutter" bruges kun point, så rækkefølgen ved pointlighed er tilfældig. Det er nævnt i artiklen. |
| **"Point tabt fra føring"** | 3 minus point i alle kampe, hvor holdet på et tidspunkt var foran. | En kamp, hvor man førte 1-0 og tabte 1-2, tæller som 3 tabte point. Man kunne også bruge "førte ved pausen" som definition. Graf 2 i artiklen viser den variant. |
| **Skrifttype** | Avenir Next (findes på Mac), derefter Helvetica Neue, Arial og en standardskrift. | Graferne gemmer teksten som former, så de ser ens ud overalt. På hjemmesiden ser besøgende uden Mac Helvetica eller Arial. **Til overvejelse:** Fontfiler som Inter kan lægges direkte på siden, så alle ser den samme skrift. Det kræver, at fontfilerne downloades, og det har jeg ikke gjort uden dig. |
| **Farver** | Accent: dansk rød `#C8102E`. Foran blå, uafgjort grå, bagud orange. | Blå/orange er et af de sikreste par ved rød-grøn-farveblindhed. Rød bruges kun til fremhævning, aldrig til "bagud". |
| **Kladder** | Kladder kan kun ses lokalt med `quarto preview --profile kladde`. Den bygger til `_kladde/`, som står i `.gitignore`. | Når `quarto render` bygger den offentlige side, bliver kladderne til tomme sider på 90 bytes og indgår ikke i søgning eller sitemap. Det har jeg kontrolleret. |
| **Forhåndsbillede ved deling** | Slået fra i artiklen (`# image:`), mens den er kladde. | Ellers ville delings-PNG'en blive kopieret til `docs/`. Fjern `#`, når artiklen udgives. |
| **Python i Quarto** | En Jupyter-kerne `superliga`, der bor inde i `.venv`. Artikler skal have `jupyter: superliga` i toppen. | Quarto valgte ellers en Python-kerne fra et andet af dine projekter ("aml"). |
| **Gamle filer** | Pladsholder-artiklen "Velkommen" er slettet, og `about.qmd` er omdøbt til `om.qmd`. | |
| **Lille rettelse** | Datoformatet i artikeloversigten bruger et hårdt mellemrum efter punktummet ("8. oktober"). | Ellers tolkede Quarto "8." som starten på en nummereret liste og ødelagde oversigten. |

**Det skal du tage stilling til:**
- [ ] Skal graferne også findes i en højere mobilversion (fx 1080×1350 til Instagram eller LinkedIn på mobil)? På smalle skærme bliver teksten i 16:9-grafer lille.
- [ ] Skrifttype: er Avenir Next okay, eller skal vi lægge Inter direkte på siden?
- [ ] GitHub-link på metodesiden og `site-url` i `_quarto.yml`, når repoet er online.
- [ ] Forfatternavnet "forfatteren" står i kildelinjen og i artiklerne. Ret det i `scripts/stil.py` og `posts/_metadata.yml`, hvis det skal være anderledes.
- [ ] Bliver GitHub-repoet **offentligt**, kan kladder læses i kildekoden (`posts/.../index.qmd` og `_freeze/`), selvom de ikke vises på siden. Skal ufærdige artikler holdes i en separat gren eller et privat repo?
- [ ] Retest af GOAL API (1–2 forespørgsler), som vi aftalte til i dag. Jeg har ikke gjort det, fordi denne omgang ikke måtte sende forespørgsler.

---

## 5. Fejl og usikkerheder i dataene

- **5 mål i 2024/25 mangler målscorer.** Kilden havde også det forkerte hold på dem. Holdet er rettet ud fra den løbende stilling, men navnet mangler stadig. Se `data/clean/kvalitet_kampe.csv`.
- **Sportmonks' "CURRENT"-stilling er inkonsistent ved forlænget spilletid.** Det er løst ved at bruge stillingen efter 2. halvleg plus målene i den forlængede spilletid.
- **Udskiftningernes retning** (ind/ud) passer i næsten alle tilfælde. Der er 2 afvigelser mod 2.807 forventede.
- **8 hændelser mangler periode-id i kilden.** Det betyder ikke noget, fordi vi selv udleder perioden af minuttet.
- **Straffesparkskonkurrencer:** Tallene (fx 1-3) er taget direkte fra kilden og er ikke krydstjekket.
- **Tillægstidens længde kendes ikke.** Intervallet "76–90+" er derfor reelt længere end 15 minutter. Det gælder også for "31–45+".
- **2026/27 er kun 9 runder.** Det er en lille stikprøve, hvor én kamp kan flytte et hold meget. Det står i artiklens metodeboks.
- **Datoerne for de sidste kampe** i 2026/27 er fra 20. september. Der er ikke hentet nye runder i nat.

---

## 6. Sådan ser du hjemmesiden lokalt

Åbn Terminal og kør:

```bash
cd ~/Desktop/superliga-data
quarto preview --profile kladde
```

Det åbner siden i din browser **med kladder** (artiklen og stiltest-siden). Stop med `Ctrl+C`.

Sådan ser den **offentlige** version ud, altså uden kladder:

```bash
quarto preview
```

Sådan bygger du den færdige side til `docs/`, som GitHub Pages skal vise:

```bash
quarto render
```

Stiltest-siden ligger på `http://localhost:<port>/stiltest.html`, når kladde-previewen kører.

Hvis du ændrer i data og vil regne alle analyser igen:

```bash
.venv/bin/python scripts/rens.py && .venv/bin/python scripts/kvalitet.py && .venv/bin/python scripts/analyse.py
```

---

## 7. Forslag til næste skridt

1. **Læs artikeludkastet** og skriv dine afsnit i pladsholderne. Kig på stikordene under graferne.
2. **Hent de nye runder** i 2026/27. `scripts/hent_sportmonks.py --plan` viser prisen, som er cirka 2 kald.
3. **Retest GOAL API** med 1–2 forespørgsler, som aftalt.
4. **GitHub:** Opret et repo, push, og slå GitHub Pages til på `main` → `/docs`. Udfyld derefter `site-url` og GitHub-linket på metodesiden.
5. **Næste artikel:** Brøndby 2023/24 (idé 1) er den stærkeste historie i idébanken og kan laves med de data, vi har.
6. **Krydstjek:** Sammenlign Sportmonks med API-Football for 2022/23–2024/25 (cirka 30 kald, kræver din godkendelse). Det kan bekræfte, at de 5 mål uden målscorer og andre kildefejl er rettet korrekt.
