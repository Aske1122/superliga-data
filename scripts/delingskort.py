"""
Laver sidens standard-delingskort (billeder/delingskort.png, 1200 x 630 px).
Bruges, når en side uden egen graf deles på X, LinkedIn eller Messenger.
Artikler bruger i stedet deres egen hovedgraf (feltet 'image' i artiklen).

Kør:  .venv/bin/python scripts/delingskort.py
"""

from pathlib import Path

import matplotlib.pyplot as plt

import stil  # registrerer Inter og husets farver

ROOT = Path(__file__).resolve().parent.parent
MARINE = "#14233F"     # signaturfarven fra styles.scss
CREME = "#F4F1E8"

fig = plt.figure(figsize=(8, 4.2), dpi=150)          # 8 x 4,2 tommer ved 150 dpi = 1200 x 630 px
fig.patch.set_facecolor(MARINE)
fig.text(0.07, 0.62, "Superliga Data", fontsize=40, fontweight="semibold", color=CREME, va="center")
fig.text(0.07, 0.45, "Dansk fodbold set gennem data", fontsize=17, color=CREME, alpha=0.75, va="center")
# Signatur-detaljen: kampur-bjælken (0'–90') i grafernes orange
fig.add_artist(plt.Rectangle((0, 0), 1, 0.025, color=CREME, alpha=0.15, transform=fig.transFigure))
fig.add_artist(plt.Rectangle((0, 0), 0.62, 0.025, color=stil.BAGUD, transform=fig.transFigure))
fig.text(0.07, 0.16, "Game states · den alternative tabel · comebacks · scoringstidspunkter",
         fontsize=10.5, color=CREME, alpha=0.6)
ud = ROOT / "billeder" / "delingskort.png"
fig.savefig(ud, facecolor=MARINE)
print(f"Gemt: {ud.relative_to(ROOT)}")
