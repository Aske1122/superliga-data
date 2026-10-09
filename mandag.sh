#!/bin/bash
# Mandagens rutine: hent nyeste kampe (budgetvagten spørger om lov), rens, tjek kvaliteten,
# beregn analyserne, lav datapakken og åbn den i browseren.
# Datapakken gemmes kun lokalt i data/datapakker/ og kommer aldrig i repoet.
#
# Kør fra Terminal:  ./mandag.sh
set -e
cd "$(dirname "$0")"
echo "1/5  Henter nye kampe fra Sportmonks (svar 'ja', når budgetvagten spørger)"
.venv/bin/python scripts/hent_sportmonks.py
echo "2/5  Renser data";            .venv/bin/python scripts/rens.py > /dev/null
echo "3/5  Datakvalitetstjek";      .venv/bin/python scripts/kvalitet.py | tail -1
echo "4/5  Beregner analyser";      .venv/bin/python scripts/analyse.py > /dev/null
echo "5/5  Laver datapakken";       .venv/bin/python scripts/datapakke.py --aabn
