"""
Husstil for ALLE grafer på siden. Importér og brug sådan her:

    import stil
    fig, ax = stil.figur("Titel med pointen", "Kort undertitel, der forklarer grafen")
    ax.barh(...)
    stil.gem(fig, "mit-navn", mappe="posts/min-artikel")   # SVG til siden + PNG 1200x675 til deling

Principper (inspireret af Experimental 361):
  * lys baggrund, minimalt gitter, ingen rammer
  * én accentfarve (dansk rød) + neutrale gråtoner
  * fast palet til foran / uafgjort / bagud (blå / grå / orange), der kan skelnes af farveblinde
  * titel med pointen, undertitel, graf, og kildelinje nederst
  * hold vises med navne eller faste forkortelser fra holdnavne.csv, aldrig logoer
"""

from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.patches  # noqa: F401  (bruges som mpl.patches)
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Farver (samme værdier bruges i hjemmesidens styles.scss)
# ---------------------------------------------------------------------------
BAGGRUND = "#FAFAF7"     # næsten hvid, en anelse varm
TEKST = "#1C1C1C"        # næsten sort
GRAA_MOERK = "#5E5E5E"   # undertitler, aksetekst
GRAA = "#A3A3A3"         # neutrale søjler/linjer
GRAA_LYS = "#E4E4E0"     # gitterlinjer
ACCENT = "#C8102E"       # dansk rød: fremhæver det, grafen handler om

# Game states. Blå/orange er et af de sikreste par for rød-grøn-farveblinde.
FORAN = "#2C6FBB"
UAFGJORT = "#C9C9C4"
BAGUD = "#E08A2E"
GAME_STATE_FARVER = {"foran": FORAN, "uafgjort": UAFGJORT, "bagud": BAGUD}

KILDE = "Data: Sportmonks · Superliga Data"

# Skrifttype: første, der findes på maskinen, bruges
SKRIFT = ["Avenir Next", "Helvetica Neue", "Arial", "DejaVu Sans"]

# 8 x 4,5 tommer ved 150 dpi = 1200 x 675 pixels (16:9, passer til X og LinkedIn)
STOERRELSE = (8, 4.5)
DPI_DELING = 150


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
          figsize: tuple = STOERRELSE, venstre: float = 0.16, **kw):
    """
    Lav en figur med husets opbygning. Returnerer (fig, ax) ligesom plt.subplots.
    'venstre' er pladsen til venstre for grafen (fx til holdnavne), som andel af bredden.
    """
    fig, ax = plt.subplots(nrows, ncols, figsize=figsize, **kw)
    fig.subplots_adjust(left=venstre, right=0.96, top=0.79, bottom=0.13)
    # Titel og undertitel flugter med figurens venstre kant, ikke med grafen
    fig.text(0.03, 0.935, titel, fontsize=15, fontweight="bold", color=TEKST, ha="left", va="top")
    if undertitel:
        fig.text(0.03, 0.855, undertitel, fontsize=10.5, color=GRAA_MOERK, ha="left", va="top")
    fig.text(0.03, 0.03, KILDE, fontsize=8, color=GRAA, ha="left", va="bottom")
    return fig, ax


def farvenoegle(fig, punkter: list[tuple[str, str]]) -> None:
    """
    Farvenøgle på sin egen linje under undertitlen: små farvede firkanter med tekst.
    punkter: [("Foran", stil.FORAN), ("Uafgjort", stil.UAFGJORT), ...]
    Grafen rykkes lidt ned, så der er plads.
    """
    fig.subplots_adjust(top=0.73)
    x = 0.03
    hoejde = 0.028                                   # firkantens højde som andel af figuren
    bredde_firkant = hoejde * fig.get_figheight() / fig.get_figwidth()   # så den bliver kvadratisk
    for tekst, farve in punkter:
        fig.patches.append(mpl.patches.Rectangle((x, 0.775 - hoejde / 2), bredde_firkant, hoejde,
                                                 color=farve, transform=fig.transFigure, figure=fig))
        t = fig.text(x + bredde_firkant + 0.008, 0.775, tekst, color=GRAA_MOERK, fontsize=9.5, ha="left", va="center")
        # Mål tekstens bredde, så næste punkt placeres lige efter
        fig.canvas.draw()
        bredde = t.get_window_extent().width / fig.bbox.width
        x += bredde_firkant + 0.008 + bredde + 0.03


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


def gem(fig, navn: str, mappe: str | Path) -> dict[str, Path]:
    """
    Gem grafen to gange:
      <mappe>/figurer/<navn>.svg  til hjemmesiden (skarp på alle skærme)
      <mappe>/deling/<navn>.png   1200x675 til X/LinkedIn
    """
    mappe = ROOT / mappe
    stier = {"svg": mappe / "figurer" / f"{navn}.svg", "png": mappe / "deling" / f"{navn}.png"}
    for sti in stier.values():
        sti.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(stier["svg"])
    fig.savefig(stier["png"], dpi=DPI_DELING)   # ingen bbox_inches='tight': så bliver det præcis 1200x675
    return stier


# ---------------------------------------------------------------------------
# Hold: forkortelser og fulde navne fra vores navnetabel
# ---------------------------------------------------------------------------
_NAVNE = pd.read_csv(ROOT / "scripts" / "holdnavne.csv").drop_duplicates("hold_id").set_index("hold_id")["hold"]


def holdnavn(hold_id: str) -> str:
    """'FCK' -> 'FC København'."""
    return _NAVNE.get(hold_id, hold_id)
