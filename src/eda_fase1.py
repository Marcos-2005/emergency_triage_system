"""
Fase 1 — EDA del dataset de diálogos médico-paciente TriageIA
Salidas:
    data/processed/dataset_exploracion_fase1.csv
    reports/figures/distribucion_grupos_clinicos.png
"""
import re
import sys
import matplotlib
matplotlib.use("Agg")  # headless: no requiere display
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd
from pathlib import Path

# ── Rutas ──────────────────────────────────────────────────────────────────
ROOT        = Path(__file__).resolve().parent.parent
DATASET_DIR = ROOT / "Dataset" / "text" / "text"
OUTPUT_CSV  = ROOT / "data" / "processed" / "dataset_exploracion_fase1.csv"
OUTPUT_FIG  = ROOT / "reports" / "figures" / "distribucion_grupos_clinicos.png"

# ── Parser de diálogos ─────────────────────────────────────────────────────
def parse_dialogue(text: str) -> tuple[list[str], list[str]]:
    """
    Separa turnos D: y P: de un diálogo clínico.
    Tolera D; como variante tipográfica (detectada en CAR0002.txt).
    Maneja líneas de continuación sin etiqueta de hablante.
    Retorna (turnos_paciente, turnos_doctor).
    """
    turns_p: list[str] = []
    turns_d: list[str] = []
    speaker: str | None = None
    parts:   list[str] = []

    def _flush():
        nonlocal speaker, parts
        if speaker and parts:
            text_turn = " ".join(parts).strip()
            if text_turn:
                (turns_p if speaker == "P" else turns_d).append(text_turn)
        speaker = None
        parts = []

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            _flush()
            continue
        m = re.match(r"^([DP])[;:]\s*(.*)", line)
        if m:
            _flush()
            speaker = m.group(1)
            parts = [m.group(2)] if m.group(2) else []
        elif speaker:
            parts.append(line)

    _flush()
    return turns_p, turns_d


def _quality_flags(row: dict) -> str:
    flags = []
    total = row["n_caracteres_total"]
    if total == 0:
        return "ARCHIVO_VACIO"
    if total < 500:
        flags.append("DIALOGO_MUY_CORTO")
    if row["n_turnos_paciente"] == 0:
        flags.append("SIN_TURNOS_PACIENTE")
    if row["n_turnos_doctor"] == 0:
        flags.append("SIN_TURNOS_DOCTOR")
    if row["n_turnos_paciente"] < 3:
        flags.append("POCOS_TURNOS_P")
    ratio_p = row["n_caracteres_paciente"] / total
    if ratio_p < 0.15:
        flags.append(f"RATIO_P_BAJO({ratio_p:.0%})")
    return "; ".join(flags) if flags else "OK"


def analyze_file(filepath: Path) -> dict:
    """Extrae todas las columnas requeridas de un archivo de diálogo."""
    stem = filepath.stem  # e.g. "RES0004"
    m = re.match(r"^([A-Za-z]+)(\d+)$", stem)
    grupo = m.group(1).upper() if m else "UNKNOWN"

    # Intentar UTF-8, luego UTF-16 (BOM), luego latin-1 como último recurso.
    # RES0002.txt y RES0054.txt son UTF-16 LE con BOM.
    for enc in ("utf-8", "utf-16", "latin-1"):
        try:
            raw = filepath.read_text(encoding=enc)
            break
        except (UnicodeDecodeError, UnicodeError):
            continue
    else:
        raw = ""

    texto_completo = raw.strip()
    tiene_d_punto_coma = bool(re.search(r"^D;", texto_completo, re.MULTILINE))

    turns_p, turns_d = parse_dialogue(texto_completo)
    texto_paciente = " ".join(turns_p).strip()
    texto_doctor   = " ".join(turns_d).strip()

    row = {
        "id_caso":                stem,
        "grupo_clinico":          grupo,
        "archivo_origen":         filepath.name,
        "texto_dialogo_completo": texto_completo,
        "texto_paciente":         texto_paciente,
        "texto_doctor":           texto_doctor,
        "n_caracteres_total":     len(texto_completo),
        "n_caracteres_paciente":  len(texto_paciente),
        "n_caracteres_doctor":    len(texto_doctor),
        "n_turnos_paciente":      len(turns_p),
        "n_turnos_doctor":        len(turns_d),
        "_tiene_d_punto_coma":    tiene_d_punto_coma,  # columna interna, se descarta en CSV
        "observaciones_calidad":  "",
    }
    row["observaciones_calidad"] = _quality_flags(row)
    if tiene_d_punto_coma and row["observaciones_calidad"] == "OK":
        row["observaciones_calidad"] = "FORMATO_D_PUNTO_COMA"
    elif tiene_d_punto_coma:
        row["observaciones_calidad"] += "; FORMATO_D_PUNTO_COMA"
    return row


# ── Generación de figura ───────────────────────────────────────────────────
GROUP_COLORS = {
    "RES": "#4C72B0",
    "MSK": "#55A868",
    "GAS": "#C44E52",
    "CAR": "#8172B2",
    "DER": "#CCB974",
    "GEN": "#64B5CD",
}

def plot_distribution(dist: pd.Series, total: int, output_path: Path) -> None:
    grupos = dist.index.tolist()
    counts = dist.values.tolist()
    colors = [GROUP_COLORS.get(g, "#999999") for g in grupos]

    fig, ax = plt.subplots(figsize=(9, 5))
    bars = ax.bar(grupos, counts, color=colors, edgecolor="white", linewidth=0.8)

    for bar, count in zip(bars, counts):
        pct = count / total * 100
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 1.5,
            f"{count}\n({pct:.1f}%)",
            ha="center", va="bottom", fontsize=10, fontweight="bold",
        )

    ax.set_title(
        "Distribución de casos por grupo clínico\nDataset TriageIA — 272 diálogos médico-paciente",
        fontsize=13, pad=14,
    )
    ax.set_xlabel("Grupo clínico", fontsize=11)
    ax.set_ylabel("Número de casos", fontsize=11)
    ax.set_ylim(0, max(counts) * 1.20)
    ax.yaxis.set_major_locator(mticker.MultipleLocator(20))
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", alpha=0.3, linestyle="--")

    fig.text(
        0.5, -0.04,
        "NOTA: Desbalanceo severo — RES representa ~78% del total. Requerirá tratamiento en Fase 6-7 (class_weight o SMOTE).",
        ha="center", fontsize=8.5, color="gray", style="italic",
    )
    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()


# ── Main ───────────────────────────────────────────────────────────────────
def main() -> pd.DataFrame:
    files = sorted(DATASET_DIR.glob("*.txt"))
    if not files:
        print(f"ERROR: No se encontraron archivos .txt en {DATASET_DIR}", file=sys.stderr)
        sys.exit(1)

    print(f"Archivos encontrados: {len(files)}")
    records = [analyze_file(f) for f in files]
    df = pd.DataFrame(records)

    # ── Estadísticas ───────────────────────────────────────────────────────
    dist = df["grupo_clinico"].value_counts().sort_values(ascending=False)
    total = len(df)

    print("\n=== DISTRIBUCIÓN POR GRUPO CLÍNICO ===")
    for grupo, count in dist.items():
        print(f"  {grupo:<6} {count:>3} casos  ({count/total*100:5.1f}%)")

    print("\n=== ESTADÍSTICAS DE LONGITUD (caracteres) ===")
    for col, label in [
        ("n_caracteres_total",    "Diálogo completo"),
        ("n_caracteres_paciente", "Solo paciente   "),
        ("n_caracteres_doctor",   "Solo doctor     "),
    ]:
        s = df[col]
        print(f"  {label} — media: {s.mean():6.0f}  mediana: {s.median():6.0f}  min: {s.min():5}  max: {s.max():5}")

    print("\n=== ESTADÍSTICAS DE TURNOS ===")
    for col, label in [
        ("n_turnos_paciente", "Turnos paciente"),
        ("n_turnos_doctor",   "Turnos doctor  "),
    ]:
        s = df[col]
        print(f"  {label} — media: {s.mean():5.1f}  min: {s.min():3}  max: {s.max():3}")

    print("\n=== RATIO TEXTO PACIENTE / TOTAL (por grupo) ===")
    df["ratio_paciente"] = df["n_caracteres_paciente"] / df["n_caracteres_total"].replace(0, 1)
    for grupo in dist.index:
        r = df[df["grupo_clinico"] == grupo]["ratio_paciente"].mean()
        print(f"  {grupo:<6}  {r:.1%}")

    print("\n=== CALIDAD ===")
    fmt_sc = df["_tiene_d_punto_coma"].sum()
    print(f"  Archivos con D; (typo tipográfico): {fmt_sc}")
    problemas = df[df["observaciones_calidad"] != "OK"]
    if problemas.empty:
        print("  Sin otros problemas de calidad.")
    else:
        print(f"  Archivos con observaciones ({len(problemas)}):")
        for _, row in problemas.iterrows():
            print(f"    {row['id_caso']:<12} {row['observaciones_calidad']}")

    # ── Guardar CSV (sin columna interna) ─────────────────────────────────
    cols_csv = [c for c in df.columns if not c.startswith("_") and c != "ratio_paciente"]
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    df[cols_csv].to_csv(OUTPUT_CSV, index=False, encoding="utf-8")
    print(f"\nCSV guardado: {OUTPUT_CSV}  ({len(df)} filas, {len(cols_csv)} columnas)")

    # ── Guardar figura ─────────────────────────────────────────────────────
    plot_distribution(dist, total, OUTPUT_FIG)
    print(f"Figura guardada: {OUTPUT_FIG}")

    print("\n" + "="*60)
    print("CAPTURA REQUERIDA PARA PRESENTACIÓN:")
    print("  reports/figures/distribucion_grupos_clinicos.png")
    print("="*60)

    return df


if __name__ == "__main__":
    main()
