# TriageIA — DAG de Inferencia (Etapa B)
#
# Este DAG orquesta el pipeline de predicción para una nueva entrada:
#   Input (texto o audio) → transcripción opcional → NER → features
#   → predicción Manchester → safety rules → resultado en Postgres
#
# En Phase 2: todas las tasks son PythonOperator con placeholders.
# La lógica real se implementará en Phase 9.
#
# Trigger: manual o via API de Airflow.
# La entrada (texto o ruta de audio) se pasa como conf:
#   airflow dags trigger dag_inference --conf '{"texto": "...", "tipo": "TEXTO"}'

from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.operators.empty import EmptyOperator
from airflow.utils.dates import days_ago

default_args = {
    "owner": "triageia",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
    "email_on_failure": False,
    "email_on_retry": False,
}


# ─────────────────────────────────────────────────────────────
# Funciones placeholder
# ─────────────────────────────────────────────────────────────
def _receive_input(**context):
    """
    Phase 9: Recibe texto o audio del trigger conf.
    Genera GUID_Entrevista y registra en Postgres: estado=PENDING.
    Implementar en: src/pipeline/inference/tasks.py -> task_receive_input()
    """
    conf = context.get("dag_run").conf or {}
    print(f"[PLACEHOLDER] Task: receive_input")
    print(f"Configuración recibida: {conf}")
    print("Crearía GUID_Entrevista en Postgres. Pendiente de implementar en Phase 9.")
    # En la implementación real: context['ti'].xcom_push(key='guid', value=guid)


def _branch_audio_or_text(**context):
    """
    Decide si hay que transcribir audio o pasar directo a limpieza.
    Retorna el task_id de la rama a ejecutar.
    """
    conf = context.get("dag_run").conf or {}
    tipo = conf.get("tipo", "TEXTO")
    if tipo == "AUDIO":
        return "transcribe_audio"
    return "clean_text"


def _transcribe_audio(**context):
    """
    Phase 10 (demo): Si tipo=AUDIO, usa Whisper para transcribir.
    Actualiza Postgres: estado=TRANSCRIBED.
    Implementar en: src/pipeline/inference/tasks.py -> task_transcribe_audio()
    """
    print("[PLACEHOLDER] Task: transcribe_audio")
    print("Pendiente de implementar en Phase 10 (demo audio).")


def _clean_text(**context):
    """
    Phase 9: Aplica limpieza textual al texto de entrada.
    Reutiliza src/preprocessing/text_cleaner.py.
    Guarda texto limpio en MinIO o XCom.
    """
    print("[PLACEHOLDER] Task: clean_text")
    print("Pendiente de implementar en Phase 9.")


def _extract_entities(**context):
    """
    Phase 9: Extrae entidades clínicas con spaCy.
    Reutiliza src/extraction/ner.py.
    """
    print("[PLACEHOLDER] Task: extract_entities")
    print("Pendiente de implementar en Phase 9.")


def _build_features(**context):
    """
    Phase 9: Genera features consistentes con las del entrenamiento.
    Reutiliza src/features/feature_builder.py.
    """
    print("[PLACEHOLDER] Task: build_features")
    print("Pendiente de implementar en Phase 9.")


def _predict(**context):
    """
    Phase 9: Carga el mejor modelo desde MinIO triageia-models.
    Predice nivel Manchester + confianza.
    Actualiza Postgres: estado=PREDICTED.
    Implementar en: src/pipeline/inference/tasks.py -> task_predict()
    """
    print("[PLACEHOLDER] Task: predict")
    print("Pendiente de implementar en Phase 9.")
    # En la implementación real: retorna nivel C1-C5 + confianza via XCom


def _apply_safety_rules(**context):
    """
    Phase 9: Aplica reglas hardcodeadas (src/models/safety_rules.py).
    Keywords de alarma fuerzan C1/C2 si el modelo predijo menor urgencia.
    Registra safety_override=True si hubo cambio.
    Actualiza Postgres: estado=COMPLETED, nivel_final.
    """
    print("[PLACEHOLDER] Task: apply_safety_rules")
    print("Pendiente de implementar en Phase 9.")


def _store_result(**context):
    """
    Phase 9: Lee resultado final desde XCom.
    Guarda en Postgres tabla predicciones.
    Streamlit o API leerán directamente de Postgres.
    """
    print("[PLACEHOLDER] Task: store_result")
    print("Pendiente de implementar en Phase 9.")


# ─────────────────────────────────────────────────────────────
# Definición del DAG
# ─────────────────────────────────────────────────────────────
with DAG(
    dag_id="dag_inference",
    default_args=default_args,
    description="TriageIA — Etapa B: Pipeline de inferencia (Phase 2: esqueleto)",
    schedule_interval=None,       # Solo trigger manual
    start_date=days_ago(1),
    catchup=False,
    tags=["triageia", "inference", "etapa-b"],
) as dag:

    receive_input = PythonOperator(
        task_id="receive_input",
        python_callable=_receive_input,
    )

    branch_audio_text = BranchPythonOperator(
        task_id="branch_audio_or_text",
        python_callable=_branch_audio_or_text,
    )

    transcribe_audio = PythonOperator(
        task_id="transcribe_audio",
        python_callable=_transcribe_audio,
    )

    clean_text = PythonOperator(
        task_id="clean_text",
        python_callable=_clean_text,
        trigger_rule="none_failed_min_one_success",  # corre si branch_audio o branch_text lo selecciona
    )

    extract_entities = PythonOperator(
        task_id="extract_entities",
        python_callable=_extract_entities,
    )

    build_features = PythonOperator(
        task_id="build_features",
        python_callable=_build_features,
    )

    predict = PythonOperator(
        task_id="predict",
        python_callable=_predict,
    )

    apply_safety_rules = PythonOperator(
        task_id="apply_safety_rules",
        python_callable=_apply_safety_rules,
    )

    store_result = PythonOperator(
        task_id="store_result",
        python_callable=_store_result,
    )

    # ─────────────────────────────────────────────────────────────
    # Flujo con ramificación para audio vs texto
    # ─────────────────────────────────────────────────────────────
    receive_input >> branch_audio_text

    branch_audio_text >> transcribe_audio >> clean_text
    branch_audio_text >> clean_text

    clean_text >> extract_entities >> build_features >> predict >> apply_safety_rules >> store_result
