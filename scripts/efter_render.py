"""
Køres automatisk af Quarto efter hver 'quarto render' (se post-render i _quarto.yml).

Formål: kladder (draft: true) må ikke lække til den offentlige side.
Quarto gør selv kladdernes sider tomme, men kopierer stadig deres billeder med.
Dette script sletter alt i en kladdes mappe i docs/ undtagen den tomme index.html.
Det kører kun for den offentlige udgave (docs/), ikke for kladde-profilen (_kladde/).
"""

import os
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
output = Path(os.environ.get("QUARTO_PROJECT_OUTPUT_DIR", "docs"))
if not output.is_absolute():
    output = ROOT / output

if output.name == "docs":
    for qmd in ROOT.rglob("*.qmd"):
        if any(del_ in qmd.parts for del_ in (".venv", "_kladde", "docs", "_freeze")):
            continue
        # Er filen markeret som kladde? (kig kun i forside-metadataen mellem de første ---)
        tekst = qmd.read_text(encoding="utf-8")
        hoved = tekst.split("---")[1] if tekst.startswith("---") else ""
        if not re.search(r"^draft:\s*true", hoved, flags=re.MULTILINE):
            continue
        rel = qmd.relative_to(ROOT)
        if rel.name == "index.qmd":          # fx posts/min-artikel/index.qmd -> docs/posts/min-artikel/
            mappe = output / rel.parent
            if mappe.is_dir():
                for ting in mappe.iterdir():
                    if ting.name != "index.html":
                        shutil.rmtree(ting) if ting.is_dir() else ting.unlink()
                        print(f"  kladde-oprydning: fjernede {ting.relative_to(ROOT)}")
        else:                                 # fx stiltest.qmd -> docs/stiltest/ (billeder)
            mappe = output / rel.with_suffix("")
            if mappe.is_dir():
                shutil.rmtree(mappe)
                print(f"  kladde-oprydning: fjernede {mappe.relative_to(ROOT)}")
