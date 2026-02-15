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
CSV_DATEI = "2026-02-11T11-12_export_ohne_5000A.csv"

SPALTEN_NAMEN_ORIG = [
    "5% In",
    "20% In",
    "50% In",
    "80% In",
    "90% In",
    "100% In",
    "120% In",
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

FIG_SIZE_LINE = (20, 14)
FONT_SUBTITLE_LINE = 20
FONT_LEGEND_LINE = 24
LINE_WIDTH = 3
MARKER_SIZE = 10

FIG_SIZE_BAR = (18, 10)
FIXED_BAR_WIDTH = 0.3
BAR_SPACING = 0.02

# ==========================================
# EINHEITLICHE BEZEICHNUNGEN (Thesis-Style)
# ==========================================
LABEL_ERR_ABS = "Mittlerer absoluter Fehler |ε| [%]"
LABEL_ERR = "Übersetzungsmessabweichung ε [%]"
LABEL_I_IN = "Strom I / I_N [%]"

# --- BASIS FARBEN ---
COLOR_MBS_BASE = "#d62728"  # Rot
COLOR_CELSA_BASE = "#3187fc"  # Hellblau
COLOR_CELSA_KOMP = "#103dfc"  # Dunkelblau
COLOR_REDUR_BASE = "#1CAB10"  # Grün
COLOR_GRAY_BASE = "#6d0e78"

# Sonderfarben
COLOR_SIEMENS = "#00FFFF"  # Cyan
COLOR_3K = "#800080"  # Lila
COLOR_ROGOWSKI = "#FFA500"  # Orange


# ==========================================
# HELPER: NAMEN / LABELS
# ==========================================
def prettify_group_name(group_name: str) -> str:
    s = str(group_name).strip().replace("_", " ")
    s = re.sub(r"(?i)\bmes\b", "Messung", s)
    s = re.sub(r"(?i)\bgesamt\b", "Gesamt", s)
    s = re.sub(r"(?i)\bmessstrecke neu\b", "Messstrecke (neu)", s)
    s = re.sub(r"(?i)\bmessstrecke alt\b", "Messstrecke (alt)", s)
    s = re.sub(r"(?i)\bbuerde\b", "Bürdenvariation", s)
    s = re.sub(r"(\d+)\s*A\b", r"\1 A", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def normalize_geo(geo: str) -> str:
    g = str(geo).strip().lower()
    if "dreieck" in g:
        return "Dreieck"
    if "parallel" in g:
        return "Parallel"
    return str(geo).strip() or "?"


def format_label_text(row: pd.Series, include_current: bool = False) -> str:
    """
    Erstellt das Label im Format:
    Hersteller Modelle | Technologie | Geometrie

    Der Strom (I_N) wird NUR angehängt, wenn include_current=True (für Gesamtansicht).
    """
    h = str(row.get("hersteller", "")).strip()
    m = str(row.get("modell", "")).strip()
    t = str(row.get("technologie", "")).strip()
    geo = normalize_geo(row.get("geometrie", ""))
    ns = str(row.get("nennstrom", "")).strip()

    # Platzhalter bereinigen
    if t.lower() in ("nan", "none", ""):
        t = "-"
    if h.lower() in ("nan", "none", ""):
        h = "?"
    if m.lower() in ("nan", "none", ""):
        m = ""

    # Basis: Hersteller Modell
    base_name = f"{h} {m}".strip()

    # Aufbau: Hersteller Modell | Technologie | Geometrie
    label = f"{base_name} | {t} | {geo}"

    # Nur bei Gesamtansicht den Strom anhängen
    if include_current:
        label += f" | {ns} A"

    # Doppelte Trenner bereinigen falls Felder leer waren
    label = re.sub(r"\s+\|\s+\|\s+", " | ", label)
    return label


# ==========================================
# HELPER: DYNAMISCHES LAYOUT
# ==========================================
def calculate_layout_adjustments(data, base_height, ncol=2):
    if "hersteller" in data.columns:
        unique_items = len(
            data[["hersteller", "modell", "technologie", "geometrie"]].drop_duplicates()
        )
    else:
        unique_items = 1

    n_rows = np.ceil(unique_items / ncol)
    height_factor = 0.6 if ncol == 1 else 0.5
    extra_height = n_rows * height_factor
    total_height = base_height + extra_height

    needed_bottom_inches = 2.5 + (n_rows * 0.4)
    bottom_fraction = needed_bottom_inches / total_height
    bottom_fraction = min(0.65, max(0.2, bottom_fraction))

    return total_height, bottom_fraction


# ==========================================
# FARB-LOGIK
# ==========================================
def adjust_lightness(hex_color, factor):
    try:
        c = mcolors.cnames.get(hex_color, hex_color)
        c = mcolors.to_rgb(c)
        h, l, s = colorsys.rgb_to_hls(*c)
        l = max(0.1, min(0.9, l * factor))
        return mcolors.to_hex(colorsys.hls_to_rgb(h, l, s))
    except:
        return hex_color


def generate_color_palette(base_color, n):
    if n <= 1:
        return [base_color]
    factors = np.linspace(0.7, 1.4, n)
    palette = [adjust_lightness(base_color, f) for f in factors]
    return palette


def assign_dynamic_colors(df):
    if df.empty:
        return df
    df["_color_key"] = df["hersteller"] + "_" + df["modell"] + "_" + df["technologie"]
    unique_entries = df[
        ["hersteller", "modell", "technologie", "_color_key"]
    ].drop_duplicates()
    color_map = {}

    groups = {
        "mbs": [],
        "celsa_std": [],
        "celsa_komp": [],
        "redur": [],
        "siemens": [],
        "3-K Elektrik": [],
        "rogowski": [],
        "other": [],
    }

    for _, row in unique_entries.iterrows():
        h = str(row["hersteller"]).lower()
        t = str(row["technologie"]).lower()
        m = str(row["modell"]).lower()
        key = row["_color_key"]

        if "mbs" in h:
            groups["mbs"].append(key)
        elif "celsa" in h:
            if "kompensiert" in t:
                groups["celsa_komp"].append(key)
            else:
                groups["celsa_std"].append(key)
        elif "redur" in h or "ffp" in t:
            groups["redur"].append(key)
        elif "siemens" in h or "pac" in m:
            groups["siemens"].append(key)
        elif "k-3" in h or "3-k elektrik" in h:
            groups["3-K Elektrik"].append(key)
        elif "rogowski" in h:
            groups["rogowski"].append(key)
        else:
            groups["other"].append(key)

    for k, c in zip(
        sorted(groups["mbs"]),
        generate_color_palette(COLOR_MBS_BASE, len(groups["mbs"])),
    ):
        color_map[k] = c
    for k, c in zip(
        sorted(groups["celsa_std"]),
        generate_color_palette(COLOR_CELSA_BASE, len(groups["celsa_std"])),
    ):
        color_map[k] = c
    for k, c in zip(
        sorted(groups["celsa_komp"]),
        generate_color_palette(COLOR_CELSA_KOMP, len(groups["celsa_komp"])),
    ):
        color_map[k] = c
    for k, c in zip(
        sorted(groups["redur"]),
        generate_color_palette(COLOR_REDUR_BASE, len(groups["redur"])),
    ):
        color_map[k] = c
    for k, c in zip(
        sorted(groups["siemens"]),
        generate_color_palette(COLOR_SIEMENS, len(groups["siemens"])),
    ):
        color_map[k] = c
    for k, c in zip(
        sorted(groups["3-K Elektrik"]),
        generate_color_palette(COLOR_3K, len(groups["3-K Elektrik"])),
    ):
        color_map[k] = c
    for k, c in zip(
        sorted(groups["rogowski"]),
        generate_color_palette(COLOR_ROGOWSKI, len(groups["rogowski"])),
    ):
        color_map[k] = c
    for k, c in zip(
        sorted(groups["other"]),
        generate_color_palette(COLOR_GRAY_BASE, len(groups["other"])),
    ):
        color_map[k] = c

    df["color"] = df["_color_key"].map(color_map)
    return df


def is_dark_color(hex_color, threshold=0.4):
    try:
        c = mcolors.to_rgb(hex_color)
        lum = 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]
        return lum < threshold
    except:
        return False


# ==========================================
# SETUP
# ==========================================
def format_value(val):
    if pd.isna(val):
        return ""
    if val == 0:
        return "0.00"
    abs_val = abs(val)
    if abs_val < 0.01:
        return "< 0.01"
    return f"{val:.2f}"


def create_directories():
    for key, path in DIRS.items():
        if not os.path.exists(path):
            os.makedirs(path)


def create_dynamic_legend_handles(data, color_col="color", show_geo=True):
    legend_dict = {}
    sort_cols = [
        c
        for c in ["hersteller", "modell", "technologie", "geometrie"]
        if c in data.columns
    ]
    data_sorted = data.sort_values(by=sort_cols) if sort_cols else data
    has_geo = "geometrie" in data_sorted.columns

    for _, row in data_sorted.iterrows():
        color = row.get(color_col, "#7f7f7f")
        geo = str(row.get("geometrie", "")).strip() if has_geo else ""
        is_tri = has_geo and ("dreieck" in geo.lower())

        hatch = "///" if is_tri else None
        edge_color = "black"
        if is_tri and is_dark_color(color):
            edge_color = "white"

        # Legenden-Label OHNE Stromstärke (Standard)
        label = format_label_text(row, include_current=False)

        if label not in legend_dict:
            legend_dict[label] = Patch(
                facecolor=color,
                hatch=hatch,
                edgecolor=edge_color,
                label=label,
            )

    return list(legend_dict.values())


# ==========================================
# PLOT FUNKTIONEN
# ==========================================


def plot_range_analysis(
    data, filename, folder_key, group_name, current_val, is_gesamt=False
):
    if data.empty:
        return

    cols_low = ["5% in", "20% in", "50% in"]
    cols_nom = ["80% in", "90% in", "100% in"]
    cols_high = ["120% in"]

    def calc_mean_range(row, cols):
        vals = []
        for c in cols:
            if c in row and pd.notnull(row[c]):
                vals.append(abs(row[c]))
        return np.mean(vals) if vals else 0

    group_cols = ["nennstrom", "hersteller", "modell", "technologie", "geometrie"]
    group_cols = [c for c in group_cols if c in data.columns]

    df_agg = data.groupby(group_cols).mean(numeric_only=True).reset_index()

    df_agg["range_low"] = df_agg.apply(lambda r: calc_mean_range(r, cols_low), axis=1)
    df_agg["range_nom"] = df_agg.apply(lambda r: calc_mean_range(r, cols_nom), axis=1)
    df_agg["range_high"] = df_agg.apply(lambda r: calc_mean_range(r, cols_high), axis=1)

    if "nennstrom" in df_agg.columns:
        df_agg = df_agg.sort_values(by=["nennstrom", "hersteller", "modell"])

    dynamic_height = max(10, len(df_agg) * 1.5 + 4)
    fig, ax = plt.subplots(figsize=(20, dynamic_height))

    y_pos = np.arange(len(df_agg))
    height = 0.25

    c_low = "#00007F"
    c_nom = "#FFA400"
    c_high = "#FF0000"

    rects1 = ax.barh(
        y_pos + height,
        df_agg["range_low"],
        height,
        label="Niederstrom (5–50 % I_N)",
        color=c_low,
        edgecolor="black",
    )
    rects2 = ax.barh(
        y_pos,
        df_agg["range_nom"],
        height,
        label="Nennstrom (80–100 % I_N)",
        color=c_nom,
        edgecolor="black",
    )
    rects3 = ax.barh(
        y_pos - height,
        df_agg["range_high"],
        height,
        label="Überlast (120 % I_N)",
        color=c_high,
        edgecolor="black",
    )

    # Label-Erstellung: Strom nur bei Gesamtansicht
    y_labels = [
        format_label_text(r, include_current=is_gesamt) for _, r in df_agg.iterrows()
    ]

    ax.set_yticks(y_pos)
    ax.set_yticklabels(y_labels, fontsize=16, fontweight="bold")
    ax.set_xlabel(LABEL_ERR_ABS, fontsize=FONT_AXIS_LABEL)

    titel_str = f"Fehleranalyse nach Lastbereich – {prettify_group_name(group_name)}"
    if current_val and not is_gesamt:
        titel_str += f" ({current_val} A)"

    ax.set_title(
        titel_str,
        fontsize=FONT_TITLE,
        fontweight="bold",
        pad=20,
    )

    def label_bars(rects, x_offset):
        for rect in rects:
            width = rect.get_width()
            if width > 0:
                ax.text(
                    width + x_offset,
                    rect.get_y() + rect.get_height() / 2,
                    format_value(width),
                    va="center",
                    fontsize=12,
                    fontweight="bold",
                )

    all_vals = np.concatenate(
        [df_agg["range_low"], df_agg["range_nom"], df_agg["range_high"]]
    )
    x_max = max(all_vals) if len(all_vals) else 0
    x_offset = max(0.01, x_max * 0.01)

    label_bars(rects1, x_offset)
    label_bars(rects2, x_offset)
    label_bars(rects3, x_offset)

    if x_max > 0:
        ax.set_xlim(0, x_max * 1.15)

    ax.invert_yaxis()
    ax.grid(axis="x", linestyle="--", alpha=0.5)

    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.10), fontsize=16, ncol=3)

    plt.tight_layout()
    plt.subplots_adjust(bottom=0.2)

    full_path = os.path.join(DIRS[folder_key], filename)
    plt.savefig(full_path, dpi=300)
    print(f"Gespeichert: {full_path}")
    plt.close()


def plot_unified_bars(
    data,
    x_col,
    y_col,
    color_col,
    title,
    ylabel,
    filename,
    folder_key,
    group_name,
    sort_col=None,
):
    # Diese Funktion bleibt weitgehend gleich, da sie x-Achsen-Gruppen nutzt
    if data.empty:
        return

    if sort_col and sort_col in data.columns:
        data = data.sort_values(sort_col)

    groups = data[x_col].unique()
    try:
        groups = sorted(
            groups,
            key=lambda x: float(x) if str(x).replace(".", "", 1).isdigit() else x,
        )
    except:
        pass

    is_messstrecke = "messstrecke" in group_name.lower()
    leg_ncol = 1 if is_messstrecke else 2
    show_geo_in_legend = False

    calc_height, calc_bottom = calculate_layout_adjustments(
        data, BASE_HEIGHT_BAR, ncol=leg_ncol
    )

    plt.figure(figsize=(20, calc_height))
    ax = plt.gca()

    max_val = data[y_col].max()
    if pd.isna(max_val):
        max_val = 0
    if max_val > 0:
        ax.set_ylim(top=max_val * 1.2)

    x_positions = []
    x_labels = []

    for i, group_val in enumerate(groups):
        sub = data[data[x_col] == group_val]
        sort_col_local = (
            "sort_idx"
            if "sort_idx" in sub.columns
            else ("_sort_idx" if "_sort_idx" in sub.columns else None)
        )
        if sort_col_local:
            sub = sub.sort_values(sort_col_local)

        n_bars = len(sub)
        if n_bars == 0:
            continue

        current_group_width = n_bars * FIXED_BAR_WIDTH
        group_start_x = i - (current_group_width / 2)

        for j in range(n_bars):
            row = sub.iloc[j]
            val = row[y_col]
            color = row[color_col]
            x_pos = group_start_x + (j * FIXED_BAR_WIDTH) + (FIXED_BAR_WIDTH / 2)

            if pd.notnull(val):
                draw_width = FIXED_BAR_WIDTH * (1 - BAR_SPACING)
                current_edge_color = "white" if is_dark_color(color) else "black"

                ax.bar(
                    x_pos,
                    val,
                    width=draw_width,
                    color=color,
                    edgecolor=current_edge_color,
                    linewidth=1.5,
                )

                txt = format_value(val)
                y_pos_txt = val + (val * 0.02) if val != 0 else 0
                va_align = "bottom" if val >= 0 else "top"
                if val < 0:
                    y_pos_txt = val - (abs(val) * 0.02)

                ax.text(
                    x_pos,
                    y_pos_txt,
                    txt,
                    ha="center",
                    va=va_align,
                    fontsize=FONT_BAR_LABEL,
                    fontweight="bold",
                )

        x_positions.append(i)
        x_labels.append(str(group_val))

    ax.set_xticks(x_positions)
    ax.set_xticklabels(x_labels, fontsize=FONT_TICK_LABEL, fontweight="bold")
    ax.tick_params(axis="y", labelsize=FONT_TICK_LABEL)
    ax.set_ylabel(ylabel, fontsize=FONT_AXIS_LABEL)
    ax.set_title(title, fontsize=FONT_TITLE, fontweight="bold", pad=20)
    ax.grid(axis="y", linestyle="--", alpha=0.5)

    handles = create_dynamic_legend_handles(
        data, color_col, show_geo=show_geo_in_legend
    )
    if handles:
        ax.legend(
            handles=handles,
            loc="upper center",
            bbox_to_anchor=(0.5, -0.15),
            fontsize=FONT_TICK_LABEL,
            title="Legende",
            ncol=leg_ncol,
        )

    plt.tight_layout()
    plt.subplots_adjust(bottom=calc_bottom)

    full_path = os.path.join(DIRS[folder_key], filename)
    plt.savefig(full_path, dpi=300)
    print(f"Gespeichert: {full_path}")
    plt.close()


def plot_horizontal_generic(
    data,
    value_col,
    title,
    x_label,
    filename,
    folder_key,
    group_name,
    is_cost=False,
    is_gesamt=False,
):
    if data.empty:
        return

    sort_cols = [
        c
        for c in ["nennstrom", "hersteller", "modell", "geometrie"]
        if c in data.columns
    ]
    if sort_cols:
        if "nennstrom" in data.columns:
            data["_ns_sort"] = pd.to_numeric(data["nennstrom"], errors="coerce").fillna(
                0
            )
            sort_cols = ["_ns_sort"] + [c for c in sort_cols if c != "nennstrom"]
        data = data.sort_values(by=sort_cols, ascending=[True] * len(sort_cols))

    y_labels = []
    colors = []
    values = []
    geometries = []
    y_positions = []

    current_y = 0
    last_nennstrom = None
    GAP_SIZE = 1.5

    for _, row in data.iterrows():
        ns_val = row.get("nennstrom", "")
        # Visuelle Trennung bei neuem Nennstrom
        if last_nennstrom is not None and ns_val != last_nennstrom:
            current_y += GAP_SIZE

        # HIER: Neues Label Format nutzen
        # Strom (ns_val) wird nur angehängt, wenn is_gesamt=True
        label = format_label_text(row, include_current=is_gesamt)

        y_labels.append(label)
        colors.append(row.get("color", "#7f7f7f"))
        val = row.get(value_col, 0)
        values.append(val)
        geometries.append(str(row.get("geometrie", "")))
        y_positions.append(current_y)
        last_nennstrom = ns_val
        current_y += 1

    is_messstrecke = "messstrecke" in group_name.lower()
    leg_ncol = 1 if is_messstrecke else 2
    show_geo_in_legend = not is_messstrecke

    data_height = max(8, current_y * 0.6)
    calc_total_h, calc_bottom = calculate_layout_adjustments(
        data, data_height, ncol=leg_ncol
    )

    plt.figure(figsize=(20, calc_total_h))
    ax = plt.gca()

    bars = ax.barh(y_positions, values, color=colors, edgecolor="black", height=0.7)

    for bar, geo, col in zip(bars, geometries, colors):
        if "dreieck" in geo.lower():
            bar.set_hatch("///")
            if is_dark_color(col):
                bar.set_edgecolor("white")
                bar.set_linewidth(1.0)
            else:
                bar.set_edgecolor("black")

    max_val = max(values) if values else 0
    if max_val > 0:
        ax.set_xlim(0, max_val * 1.15)

    ax.set_yticks(y_positions)
    ax.set_yticklabels(y_labels, fontsize=16, fontweight="bold")
    ax.set_xlabel(x_label, fontsize=FONT_AXIS_LABEL)
    ax.set_title(title, fontsize=FONT_TITLE, fontweight="bold", pad=20)

    for bar, val in zip(bars, values):
        width = bar.get_width()
        if pd.isna(val):
            continue
        label_text = f"{val:.2f} €" if is_cost else format_value(val)
        text_x = width + (max_val * 0.01)
        ax.text(
            text_x,
            bar.get_y() + bar.get_height() / 2,
            label_text,
            va="center",
            fontsize=14,
            fontweight="bold",
        )

    ax.invert_yaxis()
    ax.grid(axis="x", linestyle="--", alpha=0.5)

    handles = create_dynamic_legend_handles(data, show_geo=show_geo_in_legend)
    if handles:
        ax.legend(
            handles=handles,
            loc="upper center",
            bbox_to_anchor=(0.5, -0.1),
            fontsize=14,
            ncol=leg_ncol,
        )

    plt.tight_layout()
    plt.subplots_adjust(bottom=calc_bottom)

    full_path = os.path.join(DIRS[folder_key], filename)
    plt.savefig(full_path, dpi=300)
    print(f"Gespeichert: {full_path}")
    plt.close()


def draw_limit_lines(ax, accuracy_class="1.0"):
    x_lims = [5, 20, 100, 120]
    if accuracy_class == "0.2":
        y_upper = [0.75, 0.35, 0.20, 0.20]
        y_lower = [-0.75, -0.35, -0.20, -0.20]
        label_text = "Grenzwert Kl. 0.2"
    else:
        y_upper = [3.0, 1.5, 1.0, 1.0]
        y_lower = [-3.0, -1.5, -1.0, -1.0]
        label_text = "Grenzwert Kl. 1.0"

    ax.plot(
        x_lims,
        y_upper,
        color="black",
        linestyle="--",
        linewidth=2.5,
        alpha=0.8,
        label=label_text,
    )
    ax.plot(x_lims, y_lower, color="black", linestyle="--", linewidth=2.5, alpha=0.8)


def plot_line_curves_thesis_grouped(data, group_name):
    if data.empty:
        return

    current_val = data["nennstrom"].iloc[0] if "nennstrom" in data.columns else "?"
    phase_col = "phase" if "phase" in data.columns else None

    is_messstrecke = "messstrecke" in group_name.lower()
    acc_class = "0.2" if is_messstrecke else "1.0"
    leg_ncol = 1 if is_messstrecke else 2

    print(
        f"  -> Plot Verlauf für Gruppe: {group_name} ({current_val} A) [Kl. {acc_class}]"
    )

    calc_height, calc_bottom = calculate_layout_adjustments(
        data, BASE_HEIGHT_LINE, ncol=leg_ncol
    )

    fig, axes = plt.subplots(1, 3, figsize=(20, calc_height), sharey=True)
    fig.suptitle(
        f"Genauigkeitsverlauf der Übersetzungsmessabweichung ε – I_N = {current_val} A",
        fontsize=FONT_TITLE,
        fontweight="bold",
        y=0.96,
    )

    phases = ["L1", "L2", "L3"]
    data_cols_lower = [c.lower().strip() for c in SPALTEN_NAMEN_ORIG]

    for i, ax in enumerate(axes):
        phase_name = phases[i]
        if phase_col:
            df_phase = data[
                data[phase_col]
                .astype(str)
                .str.contains(phase_name, case=False, na=False)
            ]
        else:
            df_phase = data

        ax.grid(True, which="both", linestyle="--", alpha=0.7)
        ax.axhline(0, color="black", linewidth=1)

        draw_limit_lines(ax, accuracy_class=acc_class)

        ax.set_title(f"Phase {phase_name}", fontsize=FONT_SUBTITLE_LINE, pad=10)
        ax.set_xlabel(LABEL_I_IN, fontsize=FONT_AXIS_LABEL)
        if i == 0:
            ax.set_ylabel(LABEL_ERR, fontsize=FONT_AXIS_LABEL)

        ax.set_xlim(0, 125)

        for _, row in df_phase.iterrows():
            y_vals = []
            for col_name in data_cols_lower:
                val = row.get(col_name, np.nan)
                y_vals.append(val)
            y_vals = pd.to_numeric(y_vals, errors="coerce")
            mask = ~np.isnan(y_vals)
            if not np.any(mask):
                continue

            x_plot = np.array(X_WERTE_LINIE)[mask]
            y_plot = np.array(y_vals)[mask]

            color = row["color"]
            geo = str(row.get("geometrie", "")).strip()
            linestyle = "--" if "dreieck" in geo.lower() else "-"
            marker = "^" if "dreieck" in geo.lower() else "o"

            # Auch hier: Standard Label Format
            label_txt = format_label_text(row, include_current=False)

            ax.plot(
                x_plot,
                y_plot,
                marker=marker,
                markersize=MARKER_SIZE,
                linestyle=linestyle,
                linewidth=LINE_WIDTH,
                color=color,
                label=label_txt,
            )

        ax.tick_params(axis="both", which="major", labelsize=FONT_TICK_LABEL)

    handles, labels = axes[0].get_legend_handles_labels()
    unique_items = {}
    for h, l in zip(handles, labels):
        unique_items[l] = h

    if is_messstrecke:
        final_handles = []
        final_labels = []
        sorted_keys = sorted(unique_items.keys())
        for k in sorted_keys:
            if "grenzwert" in k.lower():
                continue
            final_handles.append(unique_items[k])
            final_labels.append(k)
    else:
        parallel_list = []
        dreieck_list = []
        for lbl, hdl in unique_items.items():
            if "grenzwert" in lbl.lower():
                continue
            if "dreieck" in lbl.lower() or "circular" in lbl.lower():
                dreieck_list.append((lbl, hdl))
            else:
                parallel_list.append((lbl, hdl))

        parallel_list.sort(key=lambda x: x[0])
        dreieck_list.sort(key=lambda x: x[0])

        final_handles = []
        final_labels = []
        max_len = max(len(parallel_list), len(dreieck_list))
        for k in range(max_len):
            if k < len(parallel_list):
                final_labels.append(parallel_list[k][0])
                final_handles.append(parallel_list[k][1])
            if k < len(dreieck_list):
                final_labels.append(dreieck_list[k][0])
                final_handles.append(dreieck_list[k][1])

    if final_handles:
        legend_title = f"Klasse {acc_class}"
        fig.legend(
            final_handles,
            final_labels,
            loc="center",
            ncol=leg_ncol,
            title=legend_title,
            title_fontsize=FONT_LEGEND_LINE + 2,
            fontsize=FONT_LEGEND_LINE,
            bbox_to_anchor=(0.5, 0.12),
            frameon=True,
        )

    plt.tight_layout(rect=[0, calc_bottom, 1, 0.95])
    full_path = os.path.join(DIRS["verlauf"], f"{group_name}_verlauf.png")
    plt.savefig(full_path, dpi=300)
    print(f"Gespeichert: {full_path}")
    plt.close()


def lade_und_plotte_alle():
    create_directories()
    print(f"Lade Datei {CSV_DATEI} ...")
    if not os.path.exists(CSV_DATEI):
        print(f"Datei nicht gefunden: {CSV_DATEI}")
        return

    try:
        df = pd.read_csv(CSV_DATEI, decimal=",", thousands=".")
        if len(df.columns) < 2:
            df = pd.read_csv(CSV_DATEI, sep=";", decimal=",", thousands=".")
    except Exception as e:
        print(f"Fehler beim Lesen: {e}")
        return

    df.columns = df.columns.str.strip().str.lower()
    df = df.drop(
        columns=[c for c in df.columns if c.startswith("unnamed")], errors="ignore"
    )
    df = df.loc[:, ~df.columns.duplicated()]

    meta_cols = [
        "hersteller",
        "modell",
        "technologie",
        "geometrie",
        "nennstrom",
        "phase",
        "export_group",
    ]
    for c in meta_cols:
        if c in df.columns:
            df[c] = df[c].astype(str).str.strip()

    spalten_lower = [c.lower().strip() for c in SPALTEN_NAMEN_ORIG]
    for col in spalten_lower:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    preis_col = "preis (€)"
    if preis_col in df.columns:
        df[preis_col] = pd.to_numeric(df[preis_col], errors="coerce")

    if "export_group" not in df.columns:
        df["export_group"] = "default"

    unique_groups = df["export_group"].unique()
    print(f"Gefundene Gruppen: {unique_groups}")

    for group in unique_groups:
        print(f"\n--- Verarbeite Gruppe: {group} ---")
        df_group = df[df["export_group"] == group].copy()
        if df_group.empty:
            continue

        current_val = ""
        if "nennstrom" in df_group.columns:
            current_val = str(df_group["nennstrom"].iloc[0])

        # Check ob es sich um eine Gesamtansicht handelt (anhand des Namens oder der Vielfalt)
        is_gesamt = "gesamt" in group.lower()

        df_group = assign_dynamic_colors(df_group)

        # 1. VERLAUF
        plot_line_curves_thesis_grouped(df_group, group_name=group)

        # 2. BEREICHS-ANALYSE
        plot_range_analysis(
            df_group,
            filename=f"{group}_bereichs_analyse.png",
            folder_key="bereich",
            group_name=group,
            current_val=current_val,
            is_gesamt=is_gesamt,
        )

        # 3. AGGREGATION
        existing_cols = [c for c in spalten_lower if c in df_group.columns]
        if existing_cols:
            df_group["phase_mean_val"] = df_group[existing_cols].abs().mean(axis=1)
        else:
            df_group["phase_mean_val"] = 0

        groupby_keys = ["nennstrom", "hersteller", "modell", "technologie", "geometrie"]
        groupby_keys = [k for k in groupby_keys if k in df_group.columns]
        if not groupby_keys:
            continue

        agg_dict = {"phase_mean_val": "mean", "color": "first"}
        if preis_col in df_group.columns:
            agg_dict[preis_col] = "first"

        df_agg = df_group.groupby(groupby_keys).agg(agg_dict).reset_index()
        df_agg.rename(columns={"phase_mean_val": "total_error"}, inplace=True)

        # 4. ABSOLUTER FEHLER
        title_abs = f"Mittlerer absoluter Fehler |ε| – {prettify_group_name(group)}"
        if current_val and not is_gesamt:
            title_abs += f" ({current_val} A)"

        plot_horizontal_generic(
            df_agg,
            value_col="total_error",
            title=title_abs,
            x_label=LABEL_ERR_ABS,
            filename=f"{group}_absoluten_fehler_horizontal.png",
            folder_key="absolut",
            group_name=group,
            is_cost=False,
            is_gesamt=is_gesamt,
        )

        # 5. KOSTEN
        if preis_col in df_agg.columns:
            title_cost = f"Kostenübersicht – {prettify_group_name(group)}"
            if current_val and not is_gesamt:
                title_cost += f" ({current_val} A)"

            plot_horizontal_generic(
                df_agg,
                value_col=preis_col,
                title=title_cost,
                x_label="Kosten [€]",
                filename=f"{group}_kosten_horizontal.png",
                folder_key="kosten",
                group_name=group,
                is_cost=True,
                is_gesamt=is_gesamt,
            )

        
if __name__ == "__main__":
    lade_und_plotte_alle()
