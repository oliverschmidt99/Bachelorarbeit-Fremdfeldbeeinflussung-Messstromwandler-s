import pandas as pd
import os

# --- KONFIGURATION ---
input_file = '2026-02-11T11-12_export_ohne_5000A_ba.csv'
output_file = 'export_final.csv'

# Prüfen, ob Eingabedatei existiert
if not os.path.exists(input_file):
    print(f"Fehler: Datei '{input_file}' nicht gefunden.")
    exit(1)

print(f"Lese '{input_file}' ein...")
# WICHTIG: decimal=',' für korrekte Zahlenerkennung
df = pd.read_csv(input_file, decimal=',')

# NEU: Duplikate entfernen (falls Messungen doppelt vorkommen, z.B. durch Gruppen)
# Wir behalten den ersten Eintrag pro Legendeneintrag und Phase
print("Entferne eventuelle Duplikate...")
df = df.drop_duplicates(subset=['final_legend', 'phase'])

# Definition der Spalten
# total_score wurde hier entfernt, export_group hinzugefügt
metadata_cols = [
    'final_legend', 'hersteller', 'modell', 'geometrie',
    'nennstrom', 'technologie', 'Preis (€)', 'export_group', 'volumen'
]

value_cols = [
    '5% In', '20% In', '50% In', '80% In', '90% In', '100% In', '120% In'
]

phases = ['L1', 'L2', 'L3']

# 1. Metadata extrahieren
print("Extrahiere Metadaten...")
meta_cols_no_key = [c for c in metadata_cols if c != 'final_legend']
# Gruppieren nach final_legend und ersten Wert nehmen
df_meta = df.groupby('final_legend')[meta_cols_no_key].first().reset_index()

# 2. Pivotieren der Messwerte
print("Pivotierre Daten (Phasen nebeneinander)...")
# Hier würde es ohne drop_duplicates knallen, wenn final_legend+phase nicht eindeutig sind
df_pivot = df.pivot(index='final_legend', columns='phase', values=value_cols)

# Spaltennamen flachklopfen: "5% In" + "L1" -> "5% In_L1"
df_pivot.columns = [f'{val}_{phase}' for val, phase in df_pivot.columns]

# 3. Spalten logisch sortieren (5% L1, 5% L2, 5% L3, ...)
desired_order = []
for val in value_cols:
    for phase in phases:
        col_name = f'{val}_{phase}'
        if col_name in df_pivot.columns:
            desired_order.append(col_name)

df_pivot = df_pivot[desired_order]
df_pivot.reset_index(inplace=True)

# 4. Zusammenfügen
print("Füge Daten zusammen...")
df_final = pd.merge(df_meta, df_pivot, on='final_legend', how='left')

# 5. Sortieren
print("Sortiere Daten...")
# Hilfsspalte für Geometrie-Sortierung erstellen
# Parallel (0) soll vor Dreieck (1) kommen
# Wir nutzen .str.strip(), falls aus Versehen Leerzeichen in der Spalte sind
df_final['geo_sort'] = df_final['geometrie'].astype(str).str.strip().map({'Parallel': 0, 'Dreieck': 1})
# Falls was anderes drin steht, kommt es danach (fillna mit 2)
df_final['geo_sort'] = df_final['geo_sort'].fillna(2)

# Sortierreihenfolge: Strom -> Hersteller -> Modell -> Geometrie (Parallel zuerst)
df_final = df_final.sort_values(by=['nennstrom', 'hersteller', 'modell', 'geo_sort'])

# Hilfsspalte wieder entfernen
df_final.drop(columns=['geo_sort'], inplace=True)

# Speichern
print(f"Speichere Ergebnis in '{output_file}'...")
# WICHTIG: sep=';' und decimal=',' für deutsche Excel/CSV-Kompatibilität
df_final.to_csv(output_file, index=False, sep=';', decimal=',')

print("Fertig!")
# Kurze Vorschau der sortierten Spalten
print(df_final[['nennstrom', 'hersteller', 'modell', 'geometrie']].head(10))
