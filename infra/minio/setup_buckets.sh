#!/bin/bash
# TriageIA — Crear buckets en MinIO
#
# Prerrequisito: el stack de Docker Compose debe estar corriendo.
#
# Dos formas de ejecutar:
#
# Opción A — con mc instalado localmente:
#   chmod +x setup_buckets.sh && ./setup_buckets.sh
#
# Opción B — via Docker (sin instalar mc):
#   docker run --rm --network=host minio/mc:latest \
#     alias set triageia http://localhost:9000 minioadmin minioadmin \
#     && mc mb --ignore-existing triageia/triageia-raw \
#     && mc mb --ignore-existing triageia/triageia-processed \
#     && mc mb --ignore-existing triageia/triageia-models \
#     && mc mb --ignore-existing triageia/triageia-reports

set -e

MINIO_URL="${MINIO_URL:-http://localhost:9000}"
MINIO_USER="${MINIO_USER:-minioadmin}"
MINIO_PASS="${MINIO_PASS:-minioadmin}"
ALIAS="triageia_local"

BUCKETS=(
    "triageia-raw"        # Dataset fuente cargado desde Dataset/text/text/
    "triageia-processed"  # CSVs procesados: dataset_maestro, features
    "triageia-models"     # Artefactos .joblib de modelos entrenados
    "triageia-reports"    # Figuras y métricas para la presentación
)

echo "============================================"
echo "TriageIA — Configuración de buckets MinIO"
echo "============================================"
echo "Endpoint: $MINIO_URL"
echo ""

# Verificar que mc está disponible
if ! command -v mc &> /dev/null; then
    echo "ERROR: 'mc' (MinIO Client) no encontrado en PATH."
    echo ""
    echo "Instalar mc:"
    echo "  curl https://dl.min.io/client/mc/release/linux-amd64/mc -o /usr/local/bin/mc"
    echo "  chmod +x /usr/local/bin/mc"
    echo ""
    echo "O usar la Opción B de este script (via Docker)."
    exit 1
fi

# Esperar a que MinIO esté disponible
echo "Esperando que MinIO esté disponible..."
until curl -s "${MINIO_URL}/minio/health/live" > /dev/null 2>&1; do
    echo "  MinIO no disponible, reintentando en 3s..."
    sleep 3
done
echo "MinIO disponible."
echo ""

# Configurar alias
mc alias set "$ALIAS" "$MINIO_URL" "$MINIO_USER" "$MINIO_PASS" --quiet

# Crear buckets
for bucket in "${BUCKETS[@]}"; do
    echo "Creando bucket: $bucket"
    mc mb --ignore-existing "$ALIAS/$bucket"
done

echo ""
echo "Buckets creados correctamente:"
mc ls "$ALIAS/"
echo ""
echo "CAPTURA PRESENTACIÓN: Screenshot de esta salida o de http://localhost:9001"
