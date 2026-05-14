"""
TriageIA — Módulo de trazabilidad en Postgres.

Responsabilidades:
- Generar GUIDs para entrevistas y predicciones
- Registrar cada entrada al sistema en la tabla `entrevistas`
- Actualizar estado a lo largo del pipeline
- Registrar predicciones en la tabla `predicciones`
- Registrar ejecuciones de DAGs en la tabla `pipeline_runs`

Uso desde los DAGs de Airflow:
    from traceability.tracer import crear_entrevista, actualizar_estado
"""

from __future__ import annotations

import json
import os
import uuid
from contextlib import contextmanager
from typing import Optional

import psycopg2
import psycopg2.extras


def _get_connection_params() -> dict:
    return {
        "host": os.getenv("TRIAGEIA_DB_HOST", "localhost"),
        "port": int(os.getenv("TRIAGEIA_DB_PORT", "5432")),
        "dbname": os.getenv("TRIAGEIA_DB_NAME", "triageia_db"),
        "user": os.getenv("TRIAGEIA_DB_USER", "triageia"),
        "password": os.getenv("TRIAGEIA_DB_PASSWORD", "triageia"),
    }


@contextmanager
def _get_conn():
    conn = psycopg2.connect(**_get_connection_params())
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def crear_entrevista(
    texto: str,
    tipo_entrada: str = "TEXTO",
    fuente: str = "api",
    workflow_id: Optional[str] = None,
) -> str:
    """
    Registra una nueva entrevista en Postgres y devuelve su GUID.

    Args:
        texto: Texto clínico o transcripción sin procesar.
        tipo_entrada: 'TEXTO' o 'AUDIO'.
        fuente: Origen de la entrada ('dataset_osce', 'demo_streamlit', 'api').
        workflow_id: ID del DAG run de Airflow (opcional).

    Returns:
        guid_entrevista: UUID str de la entrevista creada.
    """
    guid = str(uuid.uuid4())
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO entrevistas
                    (guid_entrevista, workflow_id, estado, tipo_entrada, texto_raw, fuente)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (guid, workflow_id, "PENDING", tipo_entrada, texto, fuente),
            )
    return guid


def actualizar_estado(guid: str, estado: str) -> None:
    """
    Actualiza el estado de una entrevista en Postgres.

    Estados válidos: PENDING, PROCESSING, COMPLETED, FAILED.
    Si el estado es COMPLETED o FAILED, se registra timestamp_fin.
    """
    with _get_conn() as conn:
        with conn.cursor() as cur:
            if estado in ("COMPLETED", "FAILED"):
                cur.execute(
                    """
                    UPDATE entrevistas
                    SET estado = %s, timestamp_fin = NOW()
                    WHERE guid_entrevista = %s
                    """,
                    (estado, guid),
                )
            else:
                cur.execute(
                    "UPDATE entrevistas SET estado = %s WHERE guid_entrevista = %s",
                    (estado, guid),
                )


def registrar_prediccion(
    guid_entrevista: str,
    modelo_id: str,
    modelo_version: str,
    nivel_predicho: str,
    confianza: float,
    safety_override: bool = False,
    nivel_final: Optional[str] = None,
    nivel_llm_sugerido: Optional[str] = None,
    log_decisiones: Optional[dict] = None,
) -> str:
    """
    Registra el resultado de una predicción Manchester en Postgres.

    Args:
        guid_entrevista: UUID de la entrevista asociada.
        modelo_id: Nombre del modelo (e.g. 'logistic_regression').
        modelo_version: Versión del artefacto (e.g. '2026-05-14').
        nivel_predicho: Nivel Manchester predicho por el modelo (C1-C5).
        confianza: Probabilidad de la clase predicha (0.0 - 1.0).
        safety_override: True si las reglas hardcodeadas cambiaron el nivel.
        nivel_final: Nivel después de aplicar safety_rules. Si None, igual a nivel_predicho.
        nivel_llm_sugerido: Sugerencia del LLM en Phase 3 (solo para el dataset maestro).
        log_decisiones: Diccionario con trazabilidad detallada de la predicción.

    Returns:
        guid_prediccion: UUID str de la predicción creada.
    """
    guid_prediccion = str(uuid.uuid4())
    nivel_final = nivel_final or nivel_predicho

    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO predicciones (
                    guid_prediccion, guid_entrevista,
                    modelo_id, modelo_version,
                    nivel_predicho, nivel_llm_sugerido, confianza,
                    safety_override, nivel_final,
                    log_decisiones
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    guid_prediccion,
                    guid_entrevista,
                    modelo_id,
                    modelo_version,
                    nivel_predicho,
                    nivel_llm_sugerido,
                    confianza,
                    safety_override,
                    nivel_final,
                    json.dumps(log_decisiones or {}),
                ),
            )
    return guid_prediccion


def registrar_run(
    dag_id: str,
    workflow_id: str,
    estado: str,
    metricas: Optional[dict] = None,
    artefacto_uri: Optional[str] = None,
) -> str:
    """
    Registra la ejecución de un DAG run en Postgres.

    Args:
        dag_id: ID del DAG ('dag_training' o 'dag_inference').
        workflow_id: Airflow run_id.
        estado: Estado del run ('RUNNING', 'SUCCESS', 'FAILED').
        metricas: Diccionario con métricas del run (accuracy, F1, etc.).
        artefacto_uri: URI del artefacto generado en MinIO.

    Returns:
        run_id: UUID str del run registrado.
    """
    run_id = str(uuid.uuid4())
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO pipeline_runs
                    (run_id, dag_id, workflow_id, estado, metricas, artefacto_uri)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    run_id,
                    dag_id,
                    workflow_id,
                    estado,
                    json.dumps(metricas or {}),
                    artefacto_uri,
                ),
            )
    return run_id
