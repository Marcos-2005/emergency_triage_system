"""
Phase 3 — Ground Truth Manchester

Reads: data/processed/dataset_exploracion_fase1.csv  (272 rows, Phase 1 output)
Writes: data/master/dataset_maestro.csv              (272 rows + 17 columns)
Also:   uploads to MinIO triageia-processed
        registers metadata in Postgres

Columns added:
    guid_texto, origen, entidades_extraidas, entidades_normalizadas,
    nivel_llm_sugerido, razon_llm, confianza_llm, nivel_manchester,
    score_ansiedad, metodo_label, revision_humana, workflow_status,
    timestamp_procesamiento

Run:
    python src/ground_truth_fase3.py [--limit N] [--skip-llm] [--skip-minio] [--skip-postgres]

Checkpoint: every 10 cases → data/master/dataset_maestro_parcial.csv
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

# ─── Paths ───────────────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parent.parent
INPUT_CSV = ROOT / "data" / "processed" / "dataset_exploracion_fase1.csv"
OUTPUT_DIR = ROOT / "data" / "master"
OUTPUT_CSV = OUTPUT_DIR / "dataset_maestro.csv"
CHECKPOINT_CSV = OUTPUT_DIR / "dataset_maestro_parcial.csv"

MINIO_BUCKET = "triageia-processed"
MINIO_KEY = "ground_truth/dataset_maestro.csv"

# ─── Specialty → Manchester prior ────────────────────────────────────────────
# Informed by clinical literature; LLM refines this per-case.
# RES cases span C2–C5 (asthma attack vs. mild cough).
# MSK cases typically C3–C4.
# CAR cases default to C2 (cardiac risk).
# GAS cases default to C3.
SPECIALTY_PRIOR: dict[str, str] = {
    "RES": "C3",  # respiratory — broad range; LLM disambiguates
    "MSK": "C4",  # musculoskeletal — usually minor urgent
    "GAS": "C3",  # gastrointestinal — urgent
    "CAR": "C2",  # cardiac — emergency default
    "DER": "C4",  # dermatological — minor
    "GEN": "C3",  # general — urgent as conservative default
}

# ─── Anxiety/urgency keywords (basic, pre-NER) ───────────────────────────────
URGENCY_KEYWORDS = {
    10: ["can't breathe", "cannot breathe", "stop breathing", "unconscious", "not responding"],
    8: ["chest pain", "chest tightness", "heart attack", "stroke", "collapsed", "severe pain"],
    6: ["difficulty breathing", "shortness of breath", "high fever", "vomiting blood", "can't walk"],
    4: ["pain", "fever", "vomiting", "diarrhea", "dizzy", "swollen", "infection"],
    2: ["sore", "mild", "slight", "uncomfortable", "itching", "runny nose"],
}


def calcular_score_ansiedad(texto: str) -> int:
    """Keyword-based urgency score 0-10 from patient text."""
    texto_lower = texto.lower()
    score = 0
    for valor, keywords in URGENCY_KEYWORDS.items():
        for kw in keywords:
            if kw in texto_lower:
                score = max(score, valor)
    return score


def extraer_entidades_basicas(texto: str) -> list[str]:
    """
    Minimal pre-NER entity extraction by keyword matching.
    Phase 4 will replace this with spaCy NER.
    """
    entidades = []
    texto_lower = texto.lower()

    symptom_keywords = [
        "pain", "fever", "cough", "breathe", "breathing", "chest",
        "headache", "nausea", "vomiting", "diarrhea", "dizzy", "fatigue",
        "swelling", "rash", "infection", "bleeding", "weakness",
    ]
    for kw in symptom_keywords:
        if kw in texto_lower:
            entidades.append(kw)

    return sorted(set(entidades))


# ─── UUID generation ─────────────────────────────────────────────────────────

def generar_guid() -> str:
    import uuid
    return str(uuid.uuid4())


# ─── Main pipeline ───────────────────────────────────────────────────────────

def procesar_dataset(
    limit: int | None = None,
    skip_llm: bool = False,
    skip_minio: bool = False,
    skip_postgres: bool = False,
    checkpoint_cada: int = 10,
) -> pd.DataFrame:
    print(f"\n{'='*60}")
    print("TriageIA — Phase 3: Ground Truth Manchester")
    print(f"{'='*60}")
    print(f"Input:  {INPUT_CSV}")
    print(f"Output: {OUTPUT_CSV}")
    print(f"LLM:    {'SKIP' if skip_llm else 'claude-haiku-4-5-20251001'}")
    print(f"MinIO:  {'SKIP' if skip_minio else MINIO_BUCKET}")
    print(f"PG:     {'SKIP' if skip_postgres else 'enabled'}")
    print()

    # 1. Load Phase 1 CSV
    if not INPUT_CSV.exists():
        sys.exit(f"ERROR: {INPUT_CSV} not found. Run Phase 1 first.")

    df = pd.read_csv(INPUT_CSV)
    print(f"Loaded {len(df)} cases from Phase 1 CSV.")

    if limit:
        df = df.head(limit)
        print(f"Limited to first {limit} cases (--limit flag).")

    # 2. Initialize new columns
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Check for existing checkpoint (resumability)
    ya_procesados: set[str] = set()
    if CHECKPOINT_CSV.exists():
        df_checkpoint = pd.read_csv(CHECKPOINT_CSV)
        ya_procesados = set(df_checkpoint["id_caso"].astype(str).tolist())
        print(f"Checkpoint found: {len(ya_procesados)} cases already processed, resuming...")

    # 3. Process each case
    if not skip_llm:
        from src.extraction.llm_extractor import extraer_manchester
    else:
        def extraer_manchester(texto, **_):
            return {
                "sintomas": [],
                "nivel_sugerido": None,
                "razon": "LLM skipped (--skip-llm)",
                "confianza": 0.0,
            }

    rows = []
    ahora = datetime.now().isoformat()

    for idx, row in df.iterrows():
        id_caso = str(row["id_caso"])

        if id_caso in ya_procesados:
            continue

        grupo = str(row.get("grupo_clinico", "GEN")).upper()
        texto_paciente = str(row.get("texto_paciente", ""))
        texto_completo = str(row.get("texto_dialogo_completo", ""))

        # LLM call
        print(f"[{int(idx)+1:3d}/{len(df)}] {id_caso} ({grupo})...")
        llm_result = extraer_manchester(texto_paciente)

        nivel_llm = llm_result.get("nivel_sugerido")
        nivel_definitivo = nivel_llm if nivel_llm else SPECIALTY_PRIOR.get(grupo, "C3")
        metodo = "llm_sugerido" if nivel_llm else f"prior_especialidad_{grupo}"

        entidades = extraer_entidades_basicas(texto_paciente)
        score = calcular_score_ansiedad(texto_paciente)

        rows.append({
            "guid_texto": generar_guid(),
            "id_caso": id_caso,
            "grupo_clinico": grupo,
            "origen": str(row.get("archivo_origen", "")),
            "texto_dialogo_completo": texto_completo,
            "texto_paciente": texto_paciente,
            "entidades_extraidas": json.dumps(entidades),
            "entidades_normalizadas": json.dumps([]),         # Phase 4
            "nivel_llm_sugerido": nivel_llm,
            "razon_llm": llm_result.get("razon", ""),
            "confianza_llm": llm_result.get("confianza", 0.0),
            "nivel_manchester": nivel_definitivo,
            "score_ansiedad": score,
            "metodo_label": metodo,
            "revision_humana": False,
            "workflow_status": "PROCESADO",
            "timestamp_procesamiento": ahora,
        })

        # Checkpoint
        if len(rows) % checkpoint_cada == 0:
            _guardar_checkpoint(rows, df_checkpoint if ya_procesados else None)

    # 4. Combine with checkpoint if resuming
    if ya_procesados and CHECKPOINT_CSV.exists():
        df_prev = pd.read_csv(CHECKPOINT_CSV)
        df_nuevo = pd.DataFrame(rows)
        df_final = pd.concat([df_prev, df_nuevo], ignore_index=True)
    else:
        df_final = pd.DataFrame(rows)

    # 5. Save final CSV
    df_final.to_csv(OUTPUT_CSV, index=False)
    print(f"\nDataset maestro guardado: {OUTPUT_CSV} ({len(df_final)} filas)")

    # 6. Summary stats
    _imprimir_resumen(df_final)

    # 7. Upload to MinIO
    if not skip_minio:
        _subir_minio(df_final)

    # 8. Register in Postgres
    if not skip_postgres:
        _registrar_postgres(df_final)

    return df_final


def _guardar_checkpoint(rows: list[dict], df_prev=None) -> None:
    df_nuevo = pd.DataFrame(rows)
    if df_prev is not None and len(df_prev) > 0:
        df_checkpoint = pd.concat([df_prev, df_nuevo], ignore_index=True)
    else:
        df_checkpoint = df_nuevo
    df_checkpoint.to_csv(CHECKPOINT_CSV, index=False)
    print(f"  [checkpoint] {len(df_checkpoint)} casos guardados en {CHECKPOINT_CSV.name}")


def _imprimir_resumen(df: pd.DataFrame) -> None:
    print("\n--- Distribución Manchester asignada ---")
    if "nivel_manchester" in df.columns:
        dist = df["nivel_manchester"].value_counts().sort_index()
        for nivel, count in dist.items():
            pct = count / len(df) * 100
            print(f"  {nivel}: {count:3d} casos ({pct:.1f}%)")

    print("\n--- Método de asignación ---")
    if "metodo_label" in df.columns:
        for metodo, count in df["metodo_label"].value_counts().items():
            print(f"  {metodo}: {count}")

    print(f"\n--- Casos con revision_humana=False ---")
    if "revision_humana" in df.columns:
        sin_revision = (df["revision_humana"] == False).sum()
        print(f"  {sin_revision}/{len(df)} requieren revisión")


def _subir_minio(df: pd.DataFrame) -> None:
    try:
        sys.path.insert(0, str(ROOT))
        from src.traceability.storage import subir_dataframe
        uri = subir_dataframe(MINIO_BUCKET, MINIO_KEY, df)
        print(f"\nMinIO upload OK: {uri}")
    except Exception as e:
        print(f"\nWARN: MinIO upload failed (servicio no disponible): {e}")
        print("  El CSV local está guardado correctamente. Subir manualmente cuando el stack esté activo.")


def _registrar_postgres(df: pd.DataFrame) -> None:
    try:
        sys.path.insert(0, str(ROOT))
        from src.traceability.tracer import registrar_run
        metricas = {
            "total_casos": len(df),
            "distribucion_manchester": df["nivel_manchester"].value_counts().to_dict()
            if "nivel_manchester" in df.columns else {},
            "casos_sin_revision": int((df["revision_humana"] == False).sum())
            if "revision_humana" in df.columns else len(df),
        }
        run_id = registrar_run(
            dag_id="ground_truth_fase3",
            workflow_id="phase3_manual",
            estado="COMPLETED",
            metricas=metricas,
            artefacto_uri=f"minio://{MINIO_BUCKET}/{MINIO_KEY}",
        )
        print(f"Postgres run registrado: run_id={run_id}")
    except Exception as e:
        print(f"\nWARN: Postgres registration failed (servicio no disponible): {e}")
        print("  Registrar manualmente cuando el stack esté activo.")


# ─── CLI ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TriageIA Phase 3 — Ground Truth Manchester")
    parser.add_argument("--limit", type=int, default=None, help="Process only first N cases (for testing)")
    parser.add_argument("--skip-llm", action="store_true", help="Skip LLM calls (use specialty prior only)")
    parser.add_argument("--skip-minio", action="store_true", help="Skip MinIO upload")
    parser.add_argument("--skip-postgres", action="store_true", help="Skip Postgres registration")
    parser.add_argument("--checkpoint-cada", type=int, default=10, help="Checkpoint interval (cases)")
    args = parser.parse_args()

    procesar_dataset(
        limit=args.limit,
        skip_llm=args.skip_llm,
        skip_minio=args.skip_minio,
        skip_postgres=args.skip_postgres,
        checkpoint_cada=args.checkpoint_cada,
    )
