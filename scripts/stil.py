"""
Husstil for ALLE grafer på siden. Importér og brug sådan her:

    import stil
    fig, ax = stil.figur("Titel med pointen", "Kort undertitel, der forklarer grafen")
    ax.barh(...)
    stil.gem(fig, "mit-navn", mappe="posts/min-artikel")   # SVG til siden + PNG 1200x675 til deling

Mobilversion: tegn samme graf med mobil=True (stående 4:5, større tekst i forhold til bredden):
    fig, ax = stil.figur("Titel", "Undertitel", mobil=True)
    stil.gem(fig, "mit-navn", mappe="posts/min-artikel", mobil=True)
    print(stil.billede("mit-navn", "Beskrivelse til skærmlæsere"))    # <picture> der vælger version

Principper (inspireret af Experimental 361):
  * lys baggrund, minimalt gitter, ingen rammer
  * én accentfarve (dansk rød) + neutrale gråtoner
  * fast palet til foran / uafgjort / bagud (blå / grå / orange), der kan skelnes af farveblinde
  * titel med pointen, undertitel, graf, og kildelinje nederst
  * hold vises med navne eller faste forkortelser fra holdnavne.csv, aldrig logoer
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import matplotlib as mpl
import matplotlib.patches  # noqa: F401  (bruges som mpl.patches)
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Farver (samme værdier bruges i hjemmesidens styles.scss)
# ---------------------------------------------------------------------------
BAGGRUND = "#FCFBF7"     # cremehvid, samme som hjemmesiden ($papir i styles.scss)
TEKST = "#1A1A1A"        # næsten sort
GRAA_MOERK = "#6E6B64"   # undertitler, aksetekst
GRAA = "#A3A3A3"         # neutrale søjler/linjer
GRAA_LYS = "#E7E4DC"     # gitterlinjer
ACCENT = "#C8102E"       # dansk rød: fremhæver det, grafen handler om

# Game states. Blå/orange er et af de sikreste par for rød-grøn-farveblinde.
FORAN = "#2C6FBB"
UAFGJORT = "#C9C9C4"
BAGUD = "#E08A2E"
GAME_STATE_FARVER = {"foran": FORAN, "uafgjort": UAFGJORT, "bagud": BAGUD}

KILDE = "Data: Sportmonks · Superliga Data"

# Skrifttype: Inter (SIL OFL 1.1) fra projektets fonts/-mappe, samme som hjemmesiden.
# Registreres direkte hos matplotlib, så den ikke skal installeres på computeren.
from matplotlib import font_manager as _fm
for _fil in ("Inter-Regular.ttf", "Inter-SemiBold.ttf"):
    _sti = ROOT / "fonts" / _fil
    if _sti.exists():
        _fm.fontManager.addfont(str(_sti))
SKRIFT = ["Inter", "Helvetica Neue", "Arial", "DejaVu Sans"]

# To formater. Layoutet regnes i tommer, så tekst har samme fysiske størrelse i begge.
#   bred:  8 x 4,5 tommer ved 150 dpi = 1200 x 675 px (16:9, X og LinkedIn, computerskærm)
#   mobil: 3,6 x 4,5 tommer ved 300 dpi = 1080 x 1350 px (4:5, telefon, LinkedIn/Instagram på mobil).
#          Fysisk mindre end den brede, så teksten bliver større i forhold til telefonens bredde
#          (8,5 pkt. tekst ≈ 11 px på en 390 px bred skærm).
FORMATER = {
    "bred":  {"figsize": (8, 4.5), "dpi": 150, "titel": 15, "under": 10.5, "tegn_titel": 70, "tegn_under": 105},
    "mobil": {"figsize": (3.6, 4.5), "dpi": 300, "titel": 13, "under": 9.5, "tegn_titel": 30, "tegn_under": 46},
}
STOERRELSE = FORMATER["bred"]["figsize"]
DPI_DELING = FORMATER["bred"]["dpi"]
MARGEN = 0.24          # tommer fra figurens kant til titel og kildelinje


def anvend() -> None:
    """Sæt matplotlibs standarder til vores stil (kaldes automatisk ved import)."""
    mpl.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": SKRIFT,
        "font.size": 10,
        "text.color": TEKST,
        "axes.labelcolor": GRAA_MOERK,
        "axes.edgecolor": GRAA_LYS,
        "axes.facecolor": BAGGRUND,
        "figure.facecolor": BAGGRUND,
        "savefig.facecolor": BAGGRUND,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.spines.left": False,
        "axes.spines.bottom": False,
        "axes.grid": False,
        "grid.color": GRAA_LYS,
        "grid.linewidth": 0.8,
        "xtick.color": GRAA_MOERK,
        "ytick.color": TEKST,
        "xtick.major.size": 0,
        "ytick.major.size": 0,
        "axes.titlesize": 10,
        "legend.frameon": False,
        "svg.fonttype": "path",      # tekst gemmes som former, så SVG ser ens ud overalt
        "axes.formatter.use_locale": False,
    })


anvend()


# ---------------------------------------------------------------------------
# Opbygning: titel, undertitel, graf, kilde
# ---------------------------------------------------------------------------
def figur(titel: str, undertitel: str = "", nrows: int = 1, ncols: int = 1,
          mobil: bool = False, venstre: float = 0.16, figsize: tuple | None = None, **kw):
    """
    Lav en figur med husets opbygning: titel (pointen), undertitel, graf, kildelinje.
    Returnerer (fig, ax) ligesom plt.subplots.
    mobil=True giver det stående mobilformat. Lange titler ombrydes automatisk.
    'venstre' er pladsen til venstre for grafen (fx til holdnavne), som andel af bredden.
    """
    f = FORMATER["mobil" if mobil else "bred"]
    fig, ax = plt.subplots(nrows, ncols, figsize=figsize or f["figsize"], **kw)
    W, H = fig.get_figwidth(), fig.get_figheight()
    x0 = MARGEN / W
    y = 1 - MARGEN / H                                   # vi arbejder os nedad fra toppen

    titel = textwrap.fill(titel, f["tegn_titel"])
    fig.text(x0, y, titel, fontsize=f["titel"], fontweight="semibold", color=TEKST, ha="left", va="top",
             linespacing=1.15)
    y -= (titel.count("\n") + 1) * f["titel"] * 1.2 / 72 / H + 0.08 / H
    if undertitel:
        undertitel = textwrap.fill(undertitel, f["tegn_under"])
        fig.text(x0, y, undertitel, fontsize=f["under"], color=GRAA_MOERK, ha="left", va="top", linespacing=1.3)
        y -= (undertitel.count("\n") + 1) * f["under"] * 1.35 / 72 / H
    fig.text(x0, MARGEN * 0.6 / H, KILDE, fontsize=8, color=GRAA, ha="left", va="bottom")

    # Husk hvor farvenøglen skal stå, hvis den bruges
    fig._sl_noegle_y = y - 0.12 / H
    fig.subplots_adjust(left=venstre, right=1 - MARGEN / W, top=y - 0.25 / H, bottom=0.74 / H)
    return fig, ax


def farvenoegle(fig, punkter: list[tuple[str, str]]) -> None:
    """
    Farvenøgle på sin egen linje under undertitlen: små farvede firkanter med tekst.
    punkter: [("Foran", stil.FORAN), ("Uafgjort", stil.UAFGJORT), ...]
    Ombrydes til en ny linje, hvis der ikke er plads (mobil). Grafen rykkes ned, så der er plads.
    """
    W, H = fig.get_figwidth(), fig.get_figheight()
    x0 = MARGEN / W
    x, y = x0, fig._sl_noegle_y - 0.08 / H
    side = 0.12                                        # firkantens side i tommer
    linje = 0.24 / H                                   # linjehøjde
    for tekst, farve in punkter:
        t = fig.text(0, 0, tekst, color=GRAA_MOERK, fontsize=9.5, ha="left", va="center")
        fig.canvas.draw()
        bredde = t.get_window_extent().width / fig.bbox.width
        if x > x0 and x + side / W + 0.06 / W + bredde > 1 - MARGEN / W:
            x, y = x0, y - linje                       # ny linje
        fig.patches.append(mpl.patches.Rectangle((x, y - side / H / 2), side / W, side / H,
                                                 color=farve, transform=fig.transFigure, figure=fig))
        t.set_position((x + side / W + 0.06 / W, y))
        x += side / W + 0.06 / W + bredde + 0.22 / W
    fig.subplots_adjust(top=y - 0.28 / H)


def game_state_noegle(fig) -> None:
    farvenoegle(fig, [("Foran", FORAN), ("Uafgjort", UAFGJORT), ("Bagud", BAGUD)])


def gitter(ax, akse: str = "x") -> None:
    """Diskrete gitterlinjer på én akse (standard: lodrette linjer til vandrette søjler)."""
    ax.grid(axis=akse, color=GRAA_LYS, linewidth=0.8)
    ax.set_axisbelow(True)


def tal(x: float, decimaler: int = 1) -> str:
    """Dansk talformat: komma som decimaltegn, punktum som tusindtalsseparator."""
    s = f"{x:,.{decimaler}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def pct(x: float, decimaler: int = 0) -> str:
    return f"{tal(x, decimaler)} %"


def gem(fig, navn: str, mappe: str | Path, mobil: bool = False) -> dict[str, Path]:
    """
    Gem grafen to gange:
      <mappe>/figurer/<navn>.svg        til hjemmesiden (skarp, gennemsigtig baggrund)
      <mappe>/deling/<navn>.png         1200x675 til X/LinkedIn
    Med mobil=True hedder filerne <navn>-mobil.svg / .png (1080x1350).
    """
    mappe = ROOT / mappe
    navn = f"{navn}-mobil" if mobil else navn
    stier = {"svg": mappe / "figurer" / f"{navn}.svg", "png": mappe / "deling" / f"{navn}.png"}
    for sti in stier.values():
        sti.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(stier["svg"], transparent=True)   # gennemsigtig: passer til sidens baggrund
    fig.savefig(stier["png"], dpi=FORMATER["mobil" if mobil else "bred"]["dpi"])   # præcis 1200x675 / 1080x1350
    return stier


def billede(navn: str, alt: str, mappe: str = "figurer") -> str:
    """
    HTML til en graf i en artikel: telefonen får mobilversionen, større skærme den brede.
    Brug i en kodecelle med '#| output: asis':  print(stil.billede("navn", "beskrivelse"))
    """
    alt = alt.replace('"', "&quot;")
    return (f'<picture class="graf">'
            f'<source media="(max-width: 600px)" srcset="{mappe}/{navn}-mobil.svg">'
            f'<img src="{mappe}/{navn}.svg" alt="{alt}" class="img-fluid" loading="lazy"></picture>')


# ---------------------------------------------------------------------------
# Hold: forkortelser og fulde navne fra vores navnetabel
# ---------------------------------------------------------------------------
_NAVNE = pd.read_csv(ROOT / "scripts" / "holdnavne.csv").drop_duplicates("hold_id").set_index("hold_id")["hold"]


def holdnavn(hold_id: str) -> str:
    """'FCK' -> 'FC København'."""
    return _NAVNE.get(hold_id, hold_id)
