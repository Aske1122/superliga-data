"""
Datakvalitetstjek af de rensede tabeller (sender ingen forespørgsler).

Viser pr. sæson: antal kampe, og hvor mange kampe der har problemer med hændelserne.
Gemmer en liste over kampe med problemer i data/clean/kvalitet_kampe.csv.

Kør:  .venv/bin/python scripts/kvalitet.py
"""

from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
CLEAN = ROOT / "data" / "clean"

# En Superliga-sæson med 12 hold: 22 runder grundspil (132 kampe) + 10 runder slutspil (60)
# + evt. en playoff-finale om Europa/Conference League (1) = 193.
FORVENTET_PR_SAESON = 193

con = duckdb.connect(str(CLEAN / "superliga.duckdb"), read_only=True)

pr_kamp = con.sql("""
    WITH m AS (
        SELECT kamp_id,
               count(*) FILTER (WHERE side = 'hjemme') AS mh,
               count(*) FILTER (WHERE side = 'ude')    AS mu,
               count(*) FILTER (WHERE side = 'hjemme' AND periode <= 2) AS mh90,
               count(*) FILTER (WHERE side = 'ude'    AND periode <= 2) AS mu90,
               count(*) FILTER (WHERE spiller IS NULL) AS uden_spiller,
               bool_or(hold_rettet) AS rettet
        FROM maal GROUP BY kamp_id),
    s AS (SELECT kamp_id, count(*) AS n FROM udskiftninger GROUP BY kamp_id),
    k AS (SELECT kamp_id, count(*) AS n FROM kort GROUP BY kamp_id)
    SELECT km.kamp_id, km.saeson, km.kickoff_utc::DATE AS dato,
           km.hjemmehold || ' - ' || km.udehold AS kamp,
           km.hjemme_maal_90 || '-' || km.ude_maal_90 AS resultat_90,
           coalesce(m.mh90, 0) || '-' || coalesce(m.mu90, 0) AS maal_fra_haendelser,
           coalesce(m.mh90, 0) <> km.hjemme_maal_90 OR coalesce(m.mu90, 0) <> km.ude_maal_90 AS maal_passer_ikke,
           coalesce(s.n, 0) AS udskiftninger,
           coalesce(k.n, 0) AS kort,
           coalesce(m.uden_spiller, 0) AS maal_uden_spiller,
           coalesce(m.rettet, false) AS hold_rettet
    FROM kampe km
    LEFT JOIN m USING (kamp_id) LEFT JOIN s USING (kamp_id) LEFT JOIN k USING (kamp_id)
""")

print("\n=== Kampe pr. sæson ===")
print(con.sql(f"""
    SELECT saeson AS sæson,
           count(*) AS kampe,
           CASE WHEN count(*) = {FORVENTET_PR_SAESON} THEN 'ja'
                WHEN saeson = (SELECT max(saeson) FROM kampe) THEN 'i gang'
                ELSE 'NEJ' END AS komplet,
           count(*) FILTER (WHERE udskiftninger = 0 AND kort = 0 AND maal_fra_haendelser = '0-0')
               AS uden_haendelser,
           count(*) FILTER (WHERE maal_passer_ikke) AS maal_passer_ikke,
           count(*) FILTER (WHERE udskiftninger = 0) AS uden_udskiftninger,
           count(*) FILTER (WHERE maal_uden_spiller > 0) AS maal_uden_spiller,
           count(*) FILTER (WHERE hold_rettet) AS hold_rettet
    FROM pr_kamp GROUP BY saeson ORDER BY saeson
""").df().to_string(index=False))

# Tjek af udskiftningsretning: en spiller, der skiftes IND, bør ikke have scoret
# eller fået kort i samme kamp FØR skiftet. Sker det ofte, er ind/ud byttet om.
forkert_retning = con.sql("""
    SELECT count(*) FROM udskiftninger u
    JOIN (SELECT kamp_id, spiller, minut FROM maal UNION ALL SELECT kamp_id, spiller, minut FROM kort) h
      ON h.kamp_id = u.kamp_id AND h.spiller = u.spiller_ind AND h.minut < u.minut
""").fetchone()[0]
rigtig_retning = con.sql("""
    SELECT count(*) FROM udskiftninger u
    JOIN (SELECT kamp_id, spiller, minut FROM maal UNION ALL SELECT kamp_id, spiller, minut FROM kort) h
      ON h.kamp_id = u.kamp_id AND h.spiller = u.spiller_ud AND h.minut < u.minut
""").fetchone()[0]
print(f"\nUdskiftningsretning: {rigtig_retning} hændelser før skiftet for den UDskiftede spiller "
      f"(forventet), {forkert_retning} for den INDskiftede (bør være ~0)")

problemer = con.sql("""
    SELECT * FROM pr_kamp
    WHERE maal_passer_ikke OR udskiftninger = 0 OR maal_uden_spiller > 0 OR hold_rettet
    ORDER BY saeson, dato
""").df()
problemer.to_csv(CLEAN / "kvalitet_kampe.csv", index=False)
print(f"\n{len(problemer)} kampe med mindst ét problem er gemt i data/clean/kvalitet_kampe.csv")
if len(problemer):
    print(problemer.drop(columns=["kamp_id"]).to_string(index=False))
