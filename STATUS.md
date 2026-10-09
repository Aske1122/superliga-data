# Status

*Opdateret 9. oktober 2026.*

## Webadresser

- **Siden:** https://aske1122.github.io/superliga-data/
- **Koden:** https://github.com/Aske1122/superliga-data
- **Besøgstal:** https://superliga-data.goatcounter.com (virker, når kontoen er oprettet, se nedenfor)

## Det er lavet

| Del | Status |
|---|---|
| **Data** | 1.212 Superliga-kampe (2020/21–2026/27) fra Sportmonks, med mål, kort og udskiftninger. API-Football bruges som reserve. |
| **Budgetvagt** | Alle API-kald går igennem den, med dags- og timeloft, sikkerhedsmargin, cache og ingen genforsøg. |
| **Rensning og kvalitet** | Eget kildeuafhængigt format. Målene stemmer med resultatet i alle kampe. Kildefejl er rettet. Tjekket stopper med en fejlkode, hvis noget er galt. |
| **Analyser** | Game states, den alternative tabel, comebacks og føringer samt scoringstidspunkter (`scripts/analyse.py`). |
| **Design** | Tufte-inspireret med Inter og Newsreader (lokale, OFL), marineblåt topbånd, kampur-læsebjælke, rubrik med kampminut og mobilversion af alle grafer. |
| **Forside** | Pointer fra seneste runde under menuen. Indtil der er artikler, vises to grafer fra "Superligaen i tal". |
| **Superligaen i tal** | Igangværende sæson plus arkivside for hver tidligere sæson. Opdateres automatisk. |
| **Automatik** | GitHub Action mandag og torsdag kl. 06 (sommertid) / 05 (vintertid). Den er testet: den første kørsel brugte 9 API-kald, de følgende 1 kald hver. |
| **Datapakke** | `./mandag.sh` henter data og laver og åbner pakken. Eksempel: `data/datapakker/2026-27-runde-09/`. |
| **Besøgstal** | GoatCounter-scriptet ligger på siden og tæller kun på den offentlige adresse. Kontoen mangler (se nedenfor). |
| **Licenser** | Kode: MIT. Tekster og grafer: CC BY 4.0. Skrifter: OFL. |
| **Artikel** | "Silkeborgs forsvundne føringer" er en kladde med 3 grafer, stikord og metodenoter. Din tekst mangler. |

## Sådan virker automatikken

1. Mandag og torsdag morgen starter GitHub Action "Opdater data".
2. Den henter de krypterede rådata fra cachen og derefter kun de nye kampe fra Sportmonks via budgetvagten (højst 12 kald).
3. Den renser data og kører datakvalitetstjek og analysekontrol.
   - **Fejler noget, stopper den.** Siden opdateres ikke, og der oprettes et issue på GitHub (du får en e-mail).
4. Den bygger "Superligaen i tal" og forsiden igen. Udgivne artikler ændres ikke, fordi de bruger deres gemte resultater.
5. Den publicerer kun, hvis noget faktisk er ændret.

Rådata kommer aldrig i repoet. API-nøglen og krypteringsnøglen ligger som GitHub-hemmeligheder.

## Det skal du gøre fremover

- **Nu:** opret GoatCounter-kontoen (se nedenfor).
- **Mandag morgen:** kør `./mandag.sh` i Terminal fra projektmappen. Svar "ja", når budgetvagten spørger. Datapakken åbner i browseren.
- **Når du har skrevet en artikel:**
  1. Skriv din tekst i pladsholderne og slet stikord og noter til dig selv.
  2. Fjern `draft: true` i toppen.
  3. Kør `quarto render`, commit og push.
- **Hvis du får et issue fra automatikken:** åbn linket til loggen og se, hvilket tjek der fejlede.
- **Se siden lokalt med kladder:** `quarto preview --profile kladde`

### Opret GoatCounter (engangsopgave)
1. Gå til https://www.goatcounter.com/signup
2. **Code:** `superliga-data` (koden var ledig 9. oktober).
3. **Site domain:** `aske1122.github.io`
4. Udfyld din e-mail og en ny adgangskode, og tryk "Sign up".
5. Bekræft din e-mail.
6. Valgfrit: under *Settings* kan du slå tælling af dine egne besøg fra.

Scriptet ligger allerede på siden, så tallene begynder at komme, så snart kontoen findes.

## Mangler / kan forbedres

- [ ] **Artikeltekst:** Silkeborg-artiklen venter på din tekst.
- [ ] **Om-siden:** har kun titlen. Tilføj billede, tekst og links, når du er klar.
- [ ] **LinkedIn og X:** ingen links på siden endnu.
- [ ] **Budgetvagten** tæller hver for sig lokalt og i GitHub Action. Ingen risiko med de nuværende mængder (cirka 1 kald pr. kørsel), men de kender ikke hinandens forbrug.
- [ ] **Datapakken** sendes ikke automatisk. Den kan senere laves som en planlagt opgave, der sender den til dig.
- [ ] **GitHub Actions** advarer om Node 20 og om ubuntu-latest → Ubuntu 26 fra 19. oktober. Begge virker stadig, men handlingerne bør opdateres til nyere versioner med tiden.
- [ ] **Tillægstid:** den faktiske længde kendes ikke. Kampene regnes som 90 minutter (se metodesiden).
- [ ] **Dommere og tilskuere** (idé 8 og 9 i `IDEBANK.md`) kræver nye data fra Sportmonks.
- [ ] **Krydstjek mod API-Football** (2022/23–2024/25) er ikke kørt endnu. Det koster cirka 30 kald og kræver din godkendelse.
- [ ] **GOAL API** gav kun tomme svar ("warming"). Det er ikke testet igen, fordi Sportmonks dækker behovet.
