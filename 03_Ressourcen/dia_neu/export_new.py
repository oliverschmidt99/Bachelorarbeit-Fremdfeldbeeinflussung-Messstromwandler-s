import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# Einstellungen für das Diagramm
sns.set_theme(style="whitegrid")
plt.rcParams['figure.figsize'] = (12, 7)

def analyze_geometry_improvement(file_path):
    # 1. Daten laden (als String, um deutsche Formate sicher zu lesen)
    try:
        df = pd.read_csv(file_path, dtype=str)
    except FileNotFoundError:
        print(f"Fehler: Datei '{file_path}' nicht gefunden.")
        return

    # 2. Datenbereinigung
    # Spalten, die Messwerte enthalten
    load_columns = ['5% In', '20% In', '50% In', '80% In', '90% In', '100% In', '120% In']
    
    # Hilfsfunktion: Wandelt deutsche Zahlenstrings ("0,13") in Floats (0.13) um
    def clean_german_float(val):
        if pd.isna(val) or val.strip() == '':
            return np.nan
        # Entfernt Anführungszeichen und tauscht Komma gegen Punkt
        clean_val = val.replace('"', '').replace("'", '').replace(',', '.')
        try:
            return float(clean_val)
        except ValueError:
            return np.nan

    # Konvertierung anwenden
    for col in load_columns + ['Preis (€)']:
        if col in df.columns:
            df[col] = df[col].apply(clean_german_float)

    # Whitespace bei Geometrie entfernen
    if 'geometrie' in df.columns:
        df['geometrie'] = df['geometrie'].str.strip()

    # 3. Gruppierung und Berechnung
    # Wir gruppieren nach Hersteller, Modell und Nennstrom, um Paare zu finden
    group_cols = ['hersteller', 'modell', 'nennstrom']
    grouped = df.groupby(group_cols)
    
    results = []

    for name, group in grouped:
        hersteller, modell, nennstrom = name
        
        # Aufteilen in Parallel und Dreieck
        df_parallel = group[group['geometrie'] == 'Parallel']
        df_dreieck = group[group['geometrie'] == 'Dreieck']

        # Nur berechnen, wenn beide Varianten für dieses Modell vorliegen
        if not df_parallel.empty and not df_dreieck.empty:
            
            # Alle Messwerte (alle Phasen, alle Lastpunkte) in ein Array packen
            vals_parallel = df_parallel[load_columns].values.flatten()
            vals_dreieck = df_dreieck[load_columns].values.flatten()

            # NaN-Werte entfernen
            vals_parallel = vals_parallel[~np.isnan(vals_parallel)]
            vals_dreieck = vals_dreieck[~np.isnan(vals_dreieck)]

            if len(vals_parallel) > 0 and len(vals_dreieck) > 0:
                # epsilon_total berechnen (Gleichung 1): Mittelwert der Absolutbeträge
                eps_total_parallel = np.mean(np.abs(vals_parallel))
                eps_total_dreieck = np.mean(np.abs(vals_dreieck))

                # eta_geo berechnen (Gleichung 2): Verbesserung in Prozent
                if eps_total_parallel != 0:
                    eta_geo = (1 - (eps_total_dreieck / eps_total_parallel)) * 100
                else:
                    eta_geo = 0

                results.append({
                    'Label': f"{hersteller} {modell}\n({nennstrom}A)",
                    'eta_geo': eta_geo,
                    'eps_parallel': eps_total_parallel,
                    'eps_dreieck': eps_total_dreieck
                })

    # Ergebnis-DataFrame
    res_df = pd.DataFrame(results)

    if res_df.empty:
        print("Keine vollständigen Paare (Parallel & Dreieck) gefunden.")
        return

    # Sortieren nach Verbesserung
    res_df = res_df.sort_values('eta_geo', ascending=False)

    # 4. Diagramm erstellen
    plt.figure(figsize=(12, 6))
    
    # Balkendiagramm
    barplot = sns.barplot(
        data=res_df,
        x='Label',
        y='eta_geo',
        palette='viridis'
    )

    # Beschriftung und Design
    plt.ylabel(r'Geometrische Verbesserung $\eta_{geo}$ [%]', fontsize=12)
    plt.xlabel('Prüfling', fontsize=12)
    plt.title('Gesamtverbesserung durch Dreiecksanordnung (Vergleich pro Modell)', fontsize=14)
    plt.axhline(0, color='black', linewidth=0.8) # Nulllinie
    plt.xticks(rotation=45, ha='right') # Beschriftung schräg stellen

    # Werte über den Balken anzeigen
    for p in barplot.patches:
        height = p.get_height()
        if not np.isnan(height):
            plt.text(
                p.get_x() + p.get_width() / 2.,
                height + (1 if height > 0 else -3), # Position je nach Vorzeichen anpassen
                f'{height:.1f}%',
                ha="center", 
                fontsize=10, 
                fontweight='bold',
                color='black'
            )

    plt.tight_layout()
    plt.savefig('geometrische_verbesserung.png') # Speichert das Bild
    plt.show()

# --- Hauptprogramm ---
if __name__ == "__main__":
    # Dateiname anpassen
    csv_file = '2026-02-11T11-12_export_ohne_5000A.csv' 
    analyze_geometry_improvement(csv_file)