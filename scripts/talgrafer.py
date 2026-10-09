"""
Grafer og tabeller til "Superligaen i tal" (og forsiden). Kun tal og grafer, ingen fortolkning.

Hver graf-funktion tegner én graf for én sæson, i bred version eller mobilversion:
    fig = graf_gamestates(kh, "2026/27", mobil=False)
'tegn_alle' tegner og gemmer alle grafer for en sæson i begge versioner.

Alle tal kommer fra analyse.py (game states, alternativ tabel, comebacks, scoringstidspunkter).
"""

from __future__ import annotations

import html

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap

import analyse
import stil

INTERVALNAVNE = [navn for navn, _, _ in analyse.INTERVALLER]


# ---------------------------------------------------------------------------
# Hjælpere
# ---------------------------------------------------------------------------
def slug(saeson: str) -> str:
    """'2026/27' -> '2026-27' (til fil- og sidenavne)."""
    return saeson.replace("/", "-")


def runde(kh, saeson: str) -> int:
    """Antal spillede runder = flest kampe spillet af et hold i sæsonen."""
    return int(kh[kh.saeson == saeson].groupby("hold_id").size().max())


def periode_tekst(kh, saeson: str, igangvaerende: bool) -> str:
    """Fx 'Superligaen 2026/27 efter runde 9' eller 'Superligaen 2024/25, hele sæsonen'."""
    return (f"Superligaen {saeson} efter runde {runde(kh, saeson)}" if igangvaerende
            else f"Superligaen {saeson}, hele sæsonen")


def _hele(df, saeson: str):
    return df[(df.saeson == saeson) & (df.fase_gruppe == "hele_saesonen")]


# ---------------------------------------------------------------------------
# A) Game states: andel af spilletiden foran / uafgjort / bagud
# ---------------------------------------------------------------------------
def graf_gamestates(kh, saeson: str, periode: str, mobil: bool = False):
    g = _hele(analyse.game_states(kh), saeson).sort_values("netto_pct")
    fig, ax = stil.figur("Andel af spilletiden foran, uafgjort og bagud",
                         f"{periode} · sorteret efter tid foran minus tid bagud",
                         mobil=mobil, venstre=0.38 if mobil else 0.2)
    stil.game_state_noegle(fig)
    venstre = np.zeros(len(g))
    for s in ("foran", "uafgjort", "bagud"):
        vaerdi = g[f"pct_{s}"].to_numpy()
        ax.barh(g.hold, vaerdi, left=venstre, color=stil.GAME_STATE_FARVER[s], height=0.7)
        if s != "uafgjort":                      # procenttal i de farvede felter, hvis der er plads
            for y, (v, x0) in enumerate(zip(vaerdi, venstre)):
                if v >= (13 if mobil else 8):
                    ax.text(x0 + v / 2, y, f"{v:.0f}", ha="center", va="center", fontsize=7.5, color="white")
        venstre += vaerdi
    ax.set_xlim(0, 100)
    ax.xaxis.set_major_formatter(lambda x, _: stil.pct(x))
    stil.gitter(ax)
    return fig


# ---------------------------------------------------------------------------
# B) Den alternative tabel (HTML-tabel: placering hvis kampene stoppede efter X minutter)
# ---------------------------------------------------------------------------
def tabel_alternativ(kh, saeson: str) -> str:
    t = _hele(analyse.alternativ_tabel(kh), saeson).sort_values("plac_90")
    hoved = "".join(f"<th>{m}'</th>" for m in analyse.STOP_MINUTTER + [90])
    raekker = []
    for r in t.itertuples():
        celler = "".join(
            f'<td title="{getattr(r, f"point_{m}")} point">{getattr(r, f"plac_{m}")}</td>'
            for m in analyse.STOP_MINUTTER + [90])
        # Fuldt navn på store skærme, forkortelse (fx FCK) på telefoner (styres af CSS)
        navn = f"<span class='lang'>{html.escape(r.hold)}</span><span class='kort'>{r.hold_id}</span>"
        raekker.append(f"<tr><td class='hold'>{navn}</td>{celler}"
                       f"<td class='point'>{r.point_90}</td></tr>")
    return ('<div class="tabel-rul"><table class="alt-tabel">'
            f"<thead><tr><th class='hold'>Hold</th>{hoved}<th class='point'>Point</th></tr></thead>"
            f"<tbody>{''.join(raekker)}</tbody></table></div>")


# ---------------------------------------------------------------------------
# D) Comebacks og føringer: point hentet fra bagud og tabt fra føring
# ---------------------------------------------------------------------------
def graf_comebacks(kh, saeson: str, periode: str, mobil: bool = False):
    c = _hele(analyse.comebacks(kh), saeson)
    d = c.assign(netto=c.point_hentet - c.point_tabt).sort_values(["netto", "point_hentet"])
    fig, ax = stil.figur("Point hentet fra bagud og tabt fra føring",
                         f"{periode} · sorteret efter forskellen", mobil=mobil, venstre=0.38 if mobil else 0.2)
    stil.farvenoegle(fig, [("Point hentet fra bagud", stil.FORAN), ("Point tabt fra føring", stil.BAGUD)])
    y = np.arange(len(d))
    ax.barh(y, d.point_hentet, color=stil.FORAN, height=0.65)
    ax.barh(y, -d.point_tabt, color=stil.BAGUD, height=0.65)
    ax.axvline(0, color=stil.GRAA_MOERK, linewidth=0.8)
    stoerst = max(d.point_hentet.max(), d.point_tabt.max(), 1)
    luft = stoerst * 0.03
    for yi, (h, t) in enumerate(zip(d.point_hentet, d.point_tabt)):
        if h:
            ax.text(h + luft, yi, f"+{h:.0f}", va="center", fontsize=8, color=stil.FORAN)
        if t:
            ax.text(-t - luft, yi, f"−{t:.0f}", va="center", ha="right", fontsize=8, color=stil.BAGUD)
    ax.set_yticks(y, d.hold)
    graense = stoerst * (1.45 if mobil else 1.25)
    ax.set_xlim(-graense, stoerst * 1.2)
    ax.xaxis.set_major_formatter(lambda x, _: f"{abs(x):.0f}")
    ax.set_xlabel("Point")
    stil.gitter(ax)
    return fig


# ---------------------------------------------------------------------------
# C) Scoringstidspunkter: mål scoret eller indkasseret pr. 15 minutter (varmekort)
# ---------------------------------------------------------------------------
def graf_scoringer(kh, saeson: str, periode: str, retning: str = "for", mobil: bool = False):
    """retning='for' (scorede mål, blå) eller 'imod' (indkasserede mål, orange)."""
    s = _hele(analyse.scoringstidspunkter(kh), saeson)
    # Mobil: holdforkortelser (FCK, FCN ...), så selve varmekortet får mere plads
    raekke = "hold_id" if mobil else "hold"
    tabel = s.pivot_table(index=raekke, columns="interval", values=f"maal_{retning}", aggfunc="sum")
    tabel = tabel[INTERVALNAVNE].assign(_i_alt=lambda t: t.sum(axis=1)).sort_values("_i_alt")
    i_alt = tabel.pop("_i_alt")
    farve = stil.FORAN if retning == "for" else stil.BAGUD
    titel = "Mål scoret pr. 15 minutter" if retning == "for" else "Mål indkasseret pr. 15 minutter"
    fig, ax = stil.figur(titel, f"{periode} · sorteret efter antal mål i alt",
                         mobil=mobil, venstre=0.22 if mobil else 0.2)
    # Intervalnavnene står over varmekortet: ryk det ned, så de ikke rammer undertitlen
    fig.subplots_adjust(top=fig.subplotpars.top - (0.42 if mobil else 0.22) / fig.get_figheight(),
                        bottom=0.45 / fig.get_figheight())           # ingen x-akse i bunden
    cmap = LinearSegmentedColormap.from_list("skala", ["#F3F0E8", farve])
    ax.imshow(tabel.to_numpy(), aspect="auto", cmap=cmap, origin="lower")
    maks = max(tabel.to_numpy().max(), 1)
    for (yi, xi), v in np.ndenumerate(tabel.to_numpy()):
        ax.text(xi, yi, f"{v:.0f}", ha="center", va="center", fontsize=8,
                color="white" if v > maks * 0.6 else stil.TEKST)
    ax.set_yticks(range(len(tabel)), [f"{h} ({n:.0f})" for h, n in zip(tabel.index, i_alt)])
    etiketter = [n.replace("–", "–\n") for n in INTERVALNAVNE] if mobil else INTERVALNAVNE   # to linjer på mobil
    ax.set_xticks(range(len(INTERVALNAVNE)), etiketter, fontsize=7.5 if mobil else 9)
    ax.xaxis.set_ticks_position("top")
    ax.tick_params(axis="x", pad=2)
    return fig


# ---------------------------------------------------------------------------
# Tegn og gem alle grafer for en sæson (bred + mobil)
# ---------------------------------------------------------------------------
GRAFER = {
    "gamestates": lambda kh, s, p, m: graf_gamestates(kh, s, p, m),
    "comebacks": lambda kh, s, p, m: graf_comebacks(kh, s, p, m),
    "scoret": lambda kh, s, p, m: graf_scoringer(kh, s, p, "for", m),
    "indkasseret": lambda kh, s, p, m: graf_scoringer(kh, s, p, "imod", m),
}


def tegn_alle(kh, saeson: str, igangvaerende: bool, mappe: str = "tal") -> dict[str, str]:
    """Tegner alle grafer for sæsonen i begge versioner. Returnerer {graf: filnavn uden endelse}."""
    periode = periode_tekst(kh, saeson, igangvaerende)
    navne = {}
    for navn, tegn in GRAFER.items():
        filnavn = f"{slug(saeson)}-{navn}"
        for mobil in (False, True):
            fig = tegn(kh, saeson, periode, mobil)
            stil.gem(fig, filnavn, mappe, mobil=mobil)
            plt.close(fig)
        navne[navn] = filnavn
    return navne
