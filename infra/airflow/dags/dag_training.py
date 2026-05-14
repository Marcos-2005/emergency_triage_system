# TriageIA — DAG de Entrenamiento (Etapa A)
#
# Este DAG orquesta el pipeline completo de entrenamiento:
#   Dataset fuente → labels Manchester → NER → features → modelos → evaluación → auditoría
#
# En Phase 2: todas las tasks son EmptyOperator (esqueleto).
# Las tasks se implementarán en fases 3-8 con lógica real.
#
# Trigger: manual (schedule_interval=None). No se ejecuta automáticamente.
# Activar desde la UI de Airflow o con:
#   airflow dags trigger dag_training

from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago

# ─────────────────────────────────────────────────────────────
# Configuración por defecto de las tasks
# ─────────────────────────────────────────────────────────────
default_args = {
    "owner": "triageia",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
    "email_on_retry": False,
}


# ─────────────────────────────────────────────────────────────
# Funciones placeholder (se reemplazarán por imports reales en
# fases 3-8 conforme se implementen los módulos src/)
# ─────────────────────────────────────────────────────────────
def _load_raw_data(**context):
    """
    Phase 3: Lee Dataset/text/text/ y sube los 272 .txt a MinIO triageia-raw.
    Registra un GUID_Dataset en Postgres (tabla pipeline_runs).
    Implementar en: src/pipeline/training/tasks.py -> task_load_raw_data()
    """
    print("[PLACEHOLDER] Task: load_raw_data")
    print("Pendiente de implementar en Phase 3.")


def _assign_manchester_labels(**context):
    """
    Phase 3: Lee textos de MinIO triageia-raw.
    Usa Claude API para sugerir nivel Manchester por caso.
    Revisión manual de muestra. Guarda dataset_maestro.csv → MinIO triageia-processed.
    Registra en Postgres tabla entrevistas (272 filas con GUID).
    Implementar en: src/pipeline/training/tasks.py -> task_assign_labels()
    """
    print("[PLACEHOLDER] Task: assign_manchester_labels")
    print("Pendiente de implementar en Phase 3.")


def _clean_and_ner(**context):
    """
    Phase 4: Lee dataset_maestro.csv de MinIO triageia-processed.
    Aplica limpieza textual (src/preprocessing/text_cleaner.py).
    Extrae entidades clínicas con spaCy (src/extraction/ner.py).
    Guarda resultado → MinIO triageia-processed.
    Implementar en: src/pipeline/training/tasks.py -> task_clean_and_ner()
    """
    print("[PLACEHOLDER] Task: clean_and_ner")
    print("Pendiente de implementar en Phase 4.")


def _build_features(**context):
    """
    Phase 5: Lee textos procesados de MinIO triageia-processed.
    Construye matrices TF-IDF y features estructuradas.
    Guarda matrices → MinIO triageia-processed.
    Implementar en: src/pipeline/training/tasks.py -> task_build_features()
    """
    print("[PLACEHOLDER] Task: build_features")
    print("Pendiente de implementar en Phase 5.")


def _train_models(**context):
    """
    Phase 6: Lee features de MinIO triageia-processed.
    Entrena: DummyClassifier, NaiveBayes, LogisticRegression,
             LinearSVC, RandomForest, XGBoost.
    Guarda artefactos .joblib → MinIO triageia-models.
    Registra métricas en Postgres tabla pipeline_runs.
    Implementar en: src/pipeline/training/tasks.py -> task_train_models()
    """
    print("[PLACEHOLDER] Task: train_models")
    print("Pendiente de implementar en Phase 6.")


def _evaluate_and_compare(**context):
    """
    Phase 7: Lee métricas desde Postgres pipeline_runs.
    Genera tabla comparativa (accuracy, F1-macro, under-triage rate, tiempo).
    Genera figuras → MinIO triageia-reports.
    Implementar en: src/pipeline/training/tasks.py -> task_evaluate_and_compare()
    """
    print("[PLACEHOLDER] Task: evaluate_and_compare")
    print("Pendiente de implementar en Phase 7.")


def _safety_audit(**context):
    """
    Phase 8: Carga el mejor modelo desde MinIO triageia-models.
    Aplica reglas hardcodeadas (src/models/safety_rules.py).
    Calcula under-triage antes y después de las reglas.
    Guarda comparativa → MinIO triageia-reports.
    Implementar en: src/pipeline/training/tasks.py -> task_safety_audit()
    """
    print("[PLACEHOLDER] Task: safety_audit")
    print("Pendiente de implementar en Phase 8.")


# ─────────────────────────────────────────────────────────────
# Definición del DAG
# ─────────────────────────────────────────────────────────────
with DAG(
    dag_id="dag_training",
    default_args=default_args,
    description="TriageIA — Etapa A: Pipeline de entrenamiento (Phase 2: esqueleto)",
    schedule_interval=None,       # Solo trigger manual
    start_date=days_ago(1),
    catchup=False,
    tags=["triageia", "training", "etapa-a"],
) as dag:

    load_raw_data = PythonOperator(
        task_id="load_raw_data",
        python_callable=_load_raw_data,
    )

    assign_manchester_labels = PythonOperator(
        task_id="assign_manchester_labels",
        python_callable=_assign_manchester_labels,
    )

    clean_and_ner = PythonOperator(
        task_id="clean_and_ner",
        python_callable=_clean_and_ner,
    )

    build_features = PythonOperator(
        task_id="build_features",
        python_callable=_build_features,
    )

    train_models = PythonOperator(
        task_id="train_models",
        python_callable=_train_models,
    )

    evaluate_and_compare = PythonOperator(
        task_id="evaluate_and_compare",
        python_callable=_evaluate_and_compare,
    )

    safety_audit = PythonOperator(
        task_id="safety_audit",
        python_callable=_safety_audit,
    )

    # ─────────────────────────────────────────────────────────────
    # Flujo secuencial: cada task depende de la anterior
    # ─────────────────────────────────────────────────────────────
    (
        load_raw_data
        >> assign_manchester_labels
        >> clean_and_ner
        >> build_features
        >> train_models
        >> evaluate_and_compare
        >> safety_audit
    )
