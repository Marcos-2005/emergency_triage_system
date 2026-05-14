"""
TriageIA — Módulo de almacenamiento en MinIO.

Responsabilidades:
- Subir y descargar archivos desde/hacia los buckets de MinIO
- Subir DataFrames como CSV directamente desde memoria
- Generar URIs de objetos para registrar en Postgres

Buckets disponibles:
    triageia-raw        Dataset fuente cargado desde Dataset/text/text/
    triageia-processed  CSVs procesados: dataset_maestro, features
    triageia-models     Artefactos .joblib de modelos entrenados
    triageia-reports    Figuras y métricas para la presentación

Uso desde los DAGs de Airflow:
    from traceability.storage import subir_archivo, subir_dataframe
"""

from __future__ import annotations

import io
import os
from typing import Optional

import pandas as pd
from minio import Minio
from minio.error import S3Error


BUCKETS = [
    "triageia-raw",
    "triageia-processed",
    "triageia-models",
    "triageia-reports",
]


def _get_client() -> Minio:
    return Minio(
        endpoint=os.getenv("MINIO_ENDPOINT", "localhost:9000"),
        access_key=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
        secret_key=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
        secure=os.getenv("MINIO_SECURE", "false").lower() == "true",
    )


def subir_archivo(bucket: str, objeto_key: str, ruta_local: str) -> str:
    """
    Sube un archivo local a MinIO.

    Args:
        bucket: Nombre del bucket destino.
        objeto_key: Ruta del objeto dentro del bucket (e.g. 'models/lr_v1.joblib').
        ruta_local: Ruta absoluta del archivo local.

    Returns:
        URI del objeto en MinIO (e.g. 'minio://triageia-models/models/lr_v1.joblib').
    """
    client = _get_client()
    client.fput_object(bucket, objeto_key, ruta_local)
    return url_objeto(bucket, objeto_key)


def descargar_archivo(bucket: str, objeto_key: str, ruta_destino: str) -> None:
    """
    Descarga un objeto de MinIO a una ruta local.

    Args:
        bucket: Nombre del bucket origen.
        objeto_key: Ruta del objeto dentro del bucket.
        ruta_destino: Ruta local donde guardar el archivo.
    """
    client = _get_client()
    client.fget_object(bucket, objeto_key, ruta_destino)


def subir_dataframe(
    bucket: str,
    objeto_key: str,
    df: pd.DataFrame,
    index: bool = False,
) -> str:
    """
    Sube un DataFrame como CSV directamente desde memoria (sin escribir a disco).

    Args:
        bucket: Nombre del bucket destino.
        objeto_key: Ruta del objeto dentro del bucket (e.g. 'master/dataset_maestro.csv').
        df: DataFrame a subir.
        index: Si True, incluye el índice del DataFrame en el CSV.

    Returns:
        URI del objeto en MinIO.
    """
    client = _get_client()
    csv_bytes = df.to_csv(index=index).encode("utf-8")
    buffer = io.BytesIO(csv_bytes)
    client.put_object(
        bucket,
        objeto_key,
        buffer,
        length=len(csv_bytes),
        content_type="text/csv",
    )
    return url_objeto(bucket, objeto_key)


def descargar_dataframe(bucket: str, objeto_key: str) -> pd.DataFrame:
    """
    Descarga un CSV desde MinIO y lo retorna como DataFrame.

    Args:
        bucket: Nombre del bucket origen.
        objeto_key: Ruta del objeto dentro del bucket.

    Returns:
        DataFrame con los datos del CSV.
    """
    client = _get_client()
    response = client.get_object(bucket, objeto_key)
    return pd.read_csv(io.BytesIO(response.read()))


def url_objeto(bucket: str, objeto_key: str) -> str:
    """
    Genera la URI interna de un objeto en MinIO para registrar en Postgres.

    Args:
        bucket: Nombre del bucket.
        objeto_key: Ruta del objeto.

    Returns:
        URI en formato 'minio://<bucket>/<objeto_key>'.
    """
    return f"minio://{bucket}/{objeto_key}"


def objeto_existe(bucket: str, objeto_key: str) -> bool:
    """
    Verifica si un objeto existe en MinIO.

    Returns:
        True si el objeto existe, False si no.
    """
    client = _get_client()
    try:
        client.stat_object(bucket, objeto_key)
        return True
    except S3Error:
        return False
