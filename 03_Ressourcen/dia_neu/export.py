import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import colorsys
import os
import re
from matplotlib.patches import Patch
from matplotlib.ticker import MultipleLocator

# --- KONFIGURATION ---
CSV_DATEI = "export_sortiert.csv"

SPALTEN_NAMEN_ORIG = [
    "5% In", "20% In", "50% In", "80% In", "90% In", "100% In", "120% In"
]
X_WERTE_LINIE = [5, 20, 50, 80, 90, 100, 120]

# --- ORDNER ---
DIRS = {
    "verlauf": "verlauf",
    "wirtschaft": "wirtschaftlichkeit",
    "kosten": "kosten_horizontal",
    "verbesserung": "verbesserung_pct",
    "absolut": "absoluten_fehler",
    "bereich": "bereichs_analyse",
}

# --- STYLE ---
FONT_TITLE = 32
FONT_AXIS_LABEL = 18
FONT_TICK_LABEL = 16
FONT_BAR_LABEL = 14

BASE_HEIGHT_LINE = 14
BASE_HEIGHT_BAR = 10
FIXED_BAR_WIDTH = 0.3
BAR_SPACING = 0.02

# --- BASIS FARBEN (STANDARD / FLAG 0) ---
COLOR_MBS_BASE = "#d62728"   # Rot
COLOR_CELSA_BASE = "#3187fc" # Hellblau
COLOR_CELSA_KOMP = "#103dfc" # Dunkelblau
COLOR_REDUR_BASE = "#1CAB10" # Grün
COLOR_GRAY_BASE = "#6d0e78"
COLOR_SIEMENS = "#00FFFF"
COLOR_3K = "#800080"
COLOR_ROGOWSKI = "#FFA500"

# --- HARTE KONTRAST-SEQUENZ (FLAG 1) ---
# Reihenfolge wie gewünscht: Rot, Blau, Grün, Orange ...
SEQUENCE_COLORS = [
    "#d62728", # 1. ROT
    "#0000FF", # 2. BLAU
    "#00AA00", # 3. GRÜN
    "#FFA500", # 4. ORANGE
    "#800080", # 5. LILA
    "#00FFFF", # 6. CYAN
    "#A52A2A", # 7. BRAUN
    "#FF00FF", # 8. MAGENTA
    "#808080"  # 9. GRAU
]

# Farben für Bereichsanalyse
COLOR_RANGE_LOW = "#1f77b4"
COLOR_RANGE_NOM = "#2ca02c"
COLOR_RANGE_HIGH = "#d62728"

# ==========================================
# HELPER
# ==========================================

def create_directories():
    for path in DIRS.values():
        if not os.path.exists(path):
            os.makedirs(path)

def prettify_group_name(group_name: str) -> str:
    s = str(group_name).strip().replace("_", " ")
    s = re.sub(r"(?i)\bmes\b", "Messung", s)
    s = re.sub(r"(\d+)\s*A\b", r"\1 A", s)
    return s.strip()

def normalize_geo(geo: str) -> str:
    g = str(geo).strip().lower()
    if "dreieck" in g: return "Dreieck"
    if "parallel" in g: return "Parallel"
    return str(geo).strip() or "?"

def format_label_text(row: pd.Series, include_current: bool = False) -> str:
    h = str(row.get("hersteller", "")).strip()
    m = str(row.get("modell", "")).strip()
    t = str(row.get("technologie", "")).strip()
    geo = normalize_geo(row.get("geometrie", ""))
    ns = str(row.get("nennstrom", "")).strip()
    
    if t.lower() in ("nan", "none", ""): t = "-"
    if m.lower() in ("nan", "none", ""): m = ""

    label = f"{h} {m} | {t} | {geo}"
    if include_current:
        label += f" | {ns} A"
    return re.sub(r"\s+\|\s+\|\s+", " | ", label).strip()

def calculate_layout_adjustments(data, base_height, ncol=2):
    unique_items = len(data)
    n_rows = np.ceil(unique_items / ncol)
    height_factor = 0.6 if ncol == 1 else 0.5
    total_height = max(base_height, base_height + (n_rows * height_factor) - 5)
    
    needed_bottom = 2.5 + (n_rows * 0.4)
    bottom_frac = min(0.65, max(0.2, needed_bottom / total_height))
    return total_height, bottom_frac

def is_dark_color(hex_color, threshold=0.4):
    try:
        c = mcolors.to_rgb(hex_color)
        return (0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]) < threshold
    except:
        return False

def format_value(val):
    if pd.isna(val): return ""
    if val == 0: return "0.00"
    if abs(val) < 0.01: return "< 0.01"
    return f"{val:.2f}"

# ==========================================
# FARB-LOGIK (CORE)
# ==========================================

def get_standard_color(row):
    """Gibt die STANDARD-Basisfarbe zurück (für Flag 0)."""
    h = str(row.get("hersteller", "")).lower()
    t = str(row.get("technologie", "")).lower()
    if "mbs" in h: return COLOR_MBS_BASE
    if "celsa" in h: return COLOR_CELSA_KOMP if "kompensiert" in t else COLOR_CELSA_BASE
    if "redur" in h or "ffp" in t: return COLOR_REDUR_BASE
    if "siemens" in h: return COLOR_SIEMENS
    if "rogowski" in h: return COLOR_ROGOWSKI
    if "3-k" in h: return COLOR_3K
    return COLOR_GRAY_BASE

def assign_dynamic_colors_per_group(df_group):
    """
    Weist Farben basierend auf FLAGS zu.
    """
    if df_group.empty: return df_group
    
    # Flag auslesen
    flag = 0
    if "flags" in df_group.columns:
        val = df_group["flags"].iloc[0]
        try:
            if pd.notna(val): flag = int(val)
        except:
            flag = 0
            
    group_name = str(df_group["export_group"].iloc[0]) if "export_group" in df_group.columns else "?"
    print(f"   -> Gruppe '{group_name}' | Modus: {'SEQUENZ (Rot/Blau...)' if flag == 1 else 'Standard'}")

    if flag == 0:
        # --- FLAG 0: STANDARD ---
        df_group["color"] = df_group.apply(get_standard_color, axis=1)
        return df_group
        
    elif flag == 1:
        # --- FLAG 1: HARTE SEQUENZ ---
        # Farben werden strikt nach Reihenfolge vergeben:
        # 1. Messung (Par+Drei) -> Rot
        # 2. Messung (Par+Drei) -> Blau
        # usw.
        
        # Key zur Identifikation gleicher Wandlertypen
        df_group["_type_key"] = df_group["hersteller"] + "_" + df_group["modell"] + "_" + df_group["technologie"]
        
        colors_out = pd.Series(index=df_group.index, dtype=object)
        
        # Sortiere Typen (damit z.B. MBS vor Siemens kommt, oder alphabetisch)
        type_keys = sorted(df_group["_type_key"].unique())
        
        current_seq_idx = 0
        
        for type_key in type_keys:
            sub_df = df_group[df_group["_type_key"] == type_key]
            
            # Sortieren nach Legende für Konsistenz (damit Messung 1 immer Messung 1 bleibt)
            sub_df = sub_df.sort_values("final_legend")
            
            # Gruppieren nach Geometrie, um Messungs-Paare zu finden
            parallels = sub_df[sub_df["geometrie"].str.lower().str.contains("parallel")]
            triangles = sub_df[sub_df["geometrie"].str.lower().str.contains("dreieck")]
            others = sub_df[~sub_df.index.isin(parallels.index) & ~sub_df.index.isin(triangles.index)]
            
            # Anzahl der "Instanzen" dieses Typs ermitteln
            n_instances = max(len(parallels), len(triangles), 1)
            if len(others) > 0: n_instances = max(n_instances, len(others))
            
            # Zuweisung:
            # i läuft von 0 bis n_instances-1
            # Farbe kommt aus globalem Counter (current_seq_idx)
            
            for i in range(n_instances):
                # Farbe auswählen (modulo, falls mehr Messungen als Farben)
                color = SEQUENCE_COLORS[current_seq_idx % len(SEQUENCE_COLORS)]
                current_seq_idx += 1
                
                # Zuweisen an Parallel (i-te Zeile)
                if i < len(parallels):
                    colors_out[parallels.index[i]] = color
                    
                # Zuweisen an Dreieck (i-te Zeile) -> GLEICHE Farbe wie Parallel!
                if i < len(triangles):
                    colors_out[triangles.index[i]] = color
                    
                # Zuweisen an Others
                if i < len(others):
                    colors_out[others.index[i]] = color
        
        df_group["color"] = colors_out
        return df_group
    
    else:
        df_group["color"] = df_group.apply(get_standard_color, axis=1)
        return df_group

def create_dynamic_legend_handles(data, color_col="color", show_geo=True):
    legend_dict = {}
    if "nennstrom_num" in data.columns:
        data = data.sort_values(by=["nennstrom_num", "hersteller"])
        
    for _, row in data.iterrows():
        color = row.get(color_col, "#7f7f7f")
        geo = str(row.get("geometrie", "")).strip()
        is_tri = show_geo and ("dreieck" in geo.lower())
        
        hatch = "///" if is_tri else None
        edge = "white" if (is_tri and is_dark_color(color)) else "black"
        
        base_label = format_label_text(row, include_current=False)
        
        # Label deduplizieren
        label = base_label
        counter = 1
        while True:
            if label in legend_dict:
                existing_patch = legend_dict[label]
                # Wenn Farbe & Hatch gleich -> gleicher Eintrag
                if existing_patch.get_facecolor() == mcolors.to_rgba(color) and \
                   existing_patch.get_hatch() == hatch:
                    break 
                else:
                    # Gleicher Name, andere Farbe -> Zusatzinfo anhängen
                    counter += 1
                    extra = str(row.get("final_legend", ""))
                    # Versuche Datum
                    match = re.search(r'\d{4} \d{2} \d{2}', extra)
                    suffix = match.group(0) if match else f"V{counter}"
                    label = f"{base_label} ({suffix})"
            else:
                legend_dict[label] = Patch(facecolor=color, hatch=hatch, edgecolor=edge, label=label)
                break
            
    return list(legend_dict.values())

def draw_limit_lines(ax, accuracy_class="1.0"):
    x_lims = [5, 20, 100, 120]
    if accuracy_class == "0.2":
        y_vals = [0.75, 0.35, 0.20, 0.20]
        lbl = "Grenzwert Kl. 0.2"
    else:
        y_vals = [3.0, 1.5, 1.0, 1.0]
        lbl = "Grenzwert Kl. 1.0"
        
    ax.plot(x_lims, y_vals, 'k--', lw=2.5, alpha=0.8, label=lbl)
    ax.plot(x_lims, [-y for y in y_vals], 'k--', lw=2.5, alpha=0.8)

# ==========================================
# PLOT FUNKTIONEN
# ==========================================

def plot_line_curves_thesis_grouped(data, group_name):
    if data.empty: return

    current_val = data["nennstrom"].iloc[0] if "nennstrom" in data.columns else "?"
    is_messstrecke = "messstrecke" in group_name.lower()
    acc_class = "0.2" if is_messstrecke else "1.0"
    
    print(f" -> Verlauf für {group_name} ({current_val} A)")
    
    calc_h, calc_b = calculate_layout_adjustments(data, BASE_HEIGHT_LINE, ncol=2)
    fig, axes = plt.subplots(1, 3, figsize=(20, calc_h), sharey=True)
    fig.suptitle(f"Genauigkeitsverlauf – I_N = {current_val} A", fontsize=FONT_TITLE, fontweight="bold", y=0.96)
    
    phases = ["L1", "L2", "L3"]
    
    for i, ax in enumerate(axes):
        phase = phases[i]
        cols = [f"{c.lower().strip()}_{phase.lower()}" for c in SPALTEN_NAMEN_ORIG]
        
        ax.grid(True, which="both", linestyle="--", alpha=0.7)
        ax.axhline(0, color="black", linewidth=1)
        draw_limit_lines(ax, acc_class)
        
        ax.set_title(f"Phase {phase}", fontsize=20, pad=10)
        ax.set_xlabel("Strom I / I_N [%]", fontsize=FONT_AXIS_LABEL)
        if i == 0: ax.set_ylabel("Abweichung [%]", fontsize=FONT_AXIS_LABEL)
        ax.set_xlim(0, 125)
        
        for _, row in data.iterrows():
            valid_cols = [c for c in cols if c in data.columns]
            if len(valid_cols) < 3: continue 

            y_vals = pd.to_numeric(row[valid_cols], errors='coerce').values
            mask = ~np.isnan(y_vals)
            if not np.any(mask): continue
            
            x_plot = np.array(X_WERTE_LINIE)[mask]
            y_plot = y_vals[mask]
            
            col = row["color"]
            geo = str(row.get("geometrie", "")).lower()
            ls, mk = ("--", "^") if "dreieck" in geo else ("-", "o")
            
            ax.plot(x_plot, y_plot, marker=mk, markersize=10, linestyle=ls, linewidth=3, color=col)
            
        ax.tick_params(labelsize=FONT_TICK_LABEL)
        
    handles = create_dynamic_legend_handles(data)
    if handles:
        fig.legend(handles, [h.get_label() for h in handles], loc="center", ncol=2, 
                   fontsize=16, bbox_to_anchor=(0.5, 0.12))
                   
    plt.tight_layout(rect=[0, calc_b, 1, 0.95])
    full_path = os.path.join(DIRS["verlauf"], f"{group_name}_verlauf.png")
    plt.savefig(full_path, dpi=300)
    plt.close()
    print(f"Gespeichert: {full_path}")


def plot_range_analysis(data, filename, folder_key, group_name):
    cols = ["nieder_ges", "nenn_ges", "ueber_ges"]
    if not all(c in data.columns for c in cols): return

    calc_h, calc_b = calculate_layout_adjustments(data, 10, ncol=3)
    plt.figure(figsize=(20, calc_h))
    ax = plt.gca()

    y_pos = np.arange(len(data))
    height = 0.25

    ax.barh(y_pos - height, data["nieder_ges"], height, label='Niederlast', color=COLOR_RANGE_LOW, edgecolor='black')
    ax.barh(y_pos, data["nenn_ges"], height, label='Nennlast', color=COLOR_RANGE_NOM, edgecolor='black')
    ax.barh(y_pos + height, data["ueber_ges"], height, label='Überlast', color=COLOR_RANGE_HIGH, edgecolor='black')

    y_labels = [format_label_text(r) for _, r in data.iterrows()]
    ax.set_yticks(y_pos)
    ax.set_yticklabels(y_labels, fontsize=16, fontweight="bold")
    ax.set_xlabel("Mittlerer Fehler |ε| [%]", fontsize=FONT_AXIS_LABEL)
    ax.set_title(f"Fehleranalyse Bereiche – {prettify_group_name(group_name)}", fontsize=FONT_TITLE, fontweight="bold")
    
    for i, row in data.iterrows():
        for off, col in zip([-height, 0, height], cols):
            val = row[col]
            if pd.notna(val) and val != 0:
                ax.text(val + 0.01, i + off, format_value(val), va='center', fontsize=12, fontweight='bold')

    ax.invert_yaxis()
    ax.grid(axis="x", linestyle="--", alpha=0.5)
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.1), ncol=3, fontsize=14)
    
    plt.tight_layout()
    plt.subplots_adjust(bottom=calc_b)
    full_path = os.path.join(DIRS[folder_key], filename)
    plt.savefig(full_path, dpi=300)
    plt.close()
    print(f"Gespeichert: {full_path}")


def plot_horizontal_generic(data, value_col, title, x_label, filename, folder_key, is_cost=False):
    if data.empty: return
    
    df_plot = data.copy()
    
    calc_h, calc_b = calculate_layout_adjustments(df_plot, 10, ncol=2)
    plt.figure(figsize=(20, calc_h))
    ax = plt.gca()
    
    y_pos = np.arange(len(df_plot))
    bars = ax.barh(y_pos, df_plot[value_col], color=df_plot["color"], edgecolor="black", height=0.7)
    
    for i, bar in enumerate(bars):
        geo = str(df_plot.iloc[i].get("geometrie", "")).lower()
        if "dreieck" in geo:
            bar.set_hatch("///")
            if is_dark_color(df_plot.iloc[i]["color"]): bar.set_edgecolor("white")
            
    y_labels = [format_label_text(r, include_current=True) for _, r in df_plot.iterrows()]
    ax.set_yticks(y_pos)
    ax.set_yticklabels(y_labels, fontsize=16, fontweight="bold")
    ax.set_xlabel(x_label, fontsize=FONT_AXIS_LABEL)
    ax.set_title(title, fontsize=FONT_TITLE, fontweight="bold")
    
    for bar, val in zip(bars, df_plot[value_col]):
        txt = f"{val:.2f} €" if is_cost else format_value(val)
        ax.text(bar.get_width() + 0.01, bar.get_y() + bar.get_height()/2, txt, va='center', fontsize=14, fontweight="bold")
        
    ax.invert_yaxis()
    ax.grid(axis="x", linestyle="--", alpha=0.5)
    
    handles = create_dynamic_legend_handles(df_plot)
    if handles:
        ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=2, fontsize=14)
        
    plt.tight_layout()
    plt.subplots_adjust(bottom=calc_b)
    full_path = os.path.join(DIRS[folder_key], filename)
    plt.savefig(full_path, dpi=300)
    plt.close()
    print(f"Gespeichert: {full_path}")


def plot_unified_bars(data, y_col, title, ylabel, filename, folder_key):
    data = data[data[y_col].notna() & (data[y_col] != 0)].copy()
    if data.empty: return

    # Gruppierung nach Nennstrom
    grp_cols = ["nennstrom_num", "nennstrom", "hersteller", "modell", "technologie", "color"]
    df_agg = data.groupby([c for c in grp_cols if c in data.columns], as_index=False)[y_col].mean()
    
    if "nennstrom_num" in df_agg.columns:
        df_agg = df_agg.sort_values("nennstrom_num")
        groups = df_agg["nennstrom_num"].unique()
    else:
        groups = df_agg["nennstrom"].unique()
        
    calc_h, calc_b = calculate_layout_adjustments(df_agg, BASE_HEIGHT_BAR, ncol=2)
    plt.figure(figsize=(20, calc_h))
    ax = plt.gca()
    
    x_pos_list = []
    x_labels = []
    
    for i, grp in enumerate(groups):
        if "nennstrom_num" in df_agg.columns:
            sub = df_agg[df_agg["nennstrom_num"] == grp]
            label = f"{int(grp)} A"
        else:
            sub = df_agg[df_agg["nennstrom"] == grp]
            label = str(grp)
            
        n_bars = len(sub)
        width = FIXED_BAR_WIDTH
        start_x = i - (n_bars * width / 2)
        
        for j in range(n_bars):
            row = sub.iloc[j]
            val = row[y_col]
            x = start_x + j * width + width/2
            
            c = row["color"]
            edge = "white" if is_dark_color(c) else "black"
            ax.bar(x, val, width=width*0.9, color=c, edgecolor=edge)
            
            txt = format_value(val)
            y_txt = val + (0.5 if val > 0 else -0.5)
            if abs(val) < 2: y_txt = val + (2 if val > 0 else -2)
            
            ax.text(x, y_txt, txt, ha='center', va='center', fontsize=12, fontweight='bold')
            
        x_pos_list.append(i)
        x_labels.append(label)
        
    ax.set_xticks(x_pos_list)
    ax.set_xticklabels(x_labels, fontsize=16, fontweight="bold")
    ax.set_ylabel(ylabel, fontsize=18)
    ax.set_title(title, fontsize=32, fontweight="bold", pad=20)
    ax.grid(axis="y", linestyle="--", alpha=0.5)
    
    handles = create_dynamic_legend_handles(df_agg, show_geo=False)
    if handles:
        ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=2, fontsize=14)
        
    plt.tight_layout()
    plt.subplots_adjust(bottom=calc_b)
    full_path = os.path.join(DIRS[folder_key], filename)
    plt.savefig(full_path, dpi=300)
    plt.close()
    print(f"Gespeichert: {full_path}")

# ==========================================
# MAIN
# ==========================================

def lade_und_plotte_alle():
    create_directories()
    print(f"Lade Datei {CSV_DATEI} ...")
    if not os.path.exists(CSV_DATEI):
        print("Datei nicht gefunden.")
        return

    try:
        df = pd.read_csv(CSV_DATEI, sep=";", decimal=",", thousands=".")
        if len(df.columns) < 5: 
             df = pd.read_csv(CSV_DATEI, sep=",", decimal=",", thousands=".")
    except Exception as e:
        print(f"Fehler: {e}")
        return

    df.columns = df.columns.str.strip().str.lower()
    str_cols = ["hersteller", "modell", "technologie", "geometrie", "nennstrom", "export_group", "final_legend"]
    for c in str_cols:
        if c in df.columns: df[c] = df[c].astype(str).str.strip()
        
    cols_num = ["Preis (€)", "Gesamtfehler", "Verbesserung Dreick", "Nieder_Ges", "Nenn_Ges", "Ueber_Ges", "flags"]
    for c in cols_num:
        if c.lower() in df.columns: df[c.lower()] = pd.to_numeric(df[c.lower()], errors="coerce")

    if "nennstrom" in df.columns:
        df["nennstrom_num"] = pd.to_numeric(df["nennstrom"].str.replace("A", "", regex=False), errors="coerce")
        df = df.sort_values("nennstrom_num")

    if "export_group" not in df.columns:
        df["export_group"] = "default"
        
    # --- FARBEN PRO GRUPPE ZUWEISEN ---
    df_list = []
    # Reihenfolge beibehalten wichtig für Plots!
    # Wir nehmen die Unique Groups in Reihenfolge des Auftretens (wenn möglich), sonst sortiert.
    
    for grp_name, grp_df in df.groupby("export_group"):
        grp_df = assign_dynamic_colors_per_group(grp_df.copy())
        df_list.append(grp_df)
    
    df = pd.concat(df_list)
    
    # Sortierindex
    def get_sort_idx(r):
        h = str(r.get('hersteller','')).lower()
        if "mbs" in h: return 1
        if "celsa" in h: return 2
        if "redur" in h: return 4
        return 99
    df["sort_idx"] = df.apply(get_sort_idx, axis=1)

    print("\n--- Erstelle Diagramme ---")
    
    unique_groups = df["export_group"].unique()
    for group in unique_groups:
        sub = df[df["export_group"] == group].copy()
        if sub.empty: continue
        
        # 1. Verlauf
        plot_line_curves_thesis_grouped(sub, group_name=group)
        
        # 2. Bereichsanalyse
        if all(c.lower() in sub.columns for c in ["Nieder_Ges", "Nenn_Ges", "Ueber_Ges"]):
            plot_range_analysis(sub, f"{group}_bereichs_analyse.png", "bereich", group)
            
        # 3. Horizontal: Absoluter Fehler
        if "gesamtfehler" in sub.columns:
            plot_horizontal_generic(sub, "gesamtfehler", f"Absoluter Fehler – {prettify_group_name(group)}", 
                                    "Fehler [%]", f"{group}_abs_fehler.png", "absolut")
                                    
        # 4. Horizontal: Kosten
        if "preis (€)" in sub.columns:
             plot_horizontal_generic(sub, "preis (€)", f"Kosten – {prettify_group_name(group)}", 
                                    "Kosten [€]", f"{group}_kosten.png", "kosten", is_cost=True)
                                    
    # 5. Global: Verbesserung
    if "verbesserung dreick" in df.columns:
        plot_unified_bars(df, "verbesserung dreick", "Verbesserung Dreieck", "Verbesserung [%]", 
                          "verbesserung_dreieck.png", "verbesserung")

if __name__ == "__main__":
    lade_und_plotte_alle()