-- TriageIA — Schema de trazabilidad
-- Este archivo se ejecuta automáticamente cuando Postgres arranca por primera vez.
-- Crea las tablas específicas de TriageIA en triageia_db.
-- Las tablas de Airflow las crea Airflow mismo con 'airflow db init'.

-- Extensión para gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ─────────────────────────────────────────────────────────────
-- entrevistas
-- Registro de cada entrada al sistema (texto o audio).
-- Se crea al inicio del DAG de inferencia (Etapa B) o al cargar
-- el dataset en el DAG de entrenamiento (Etapa A).
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS entrevistas (
    guid_entrevista  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id      VARCHAR(128),                     -- ID del DAG run de Airflow
    timestamp_inicio TIMESTAMP DEFAULT NOW(),
    timestamp_fin    TIMESTAMP,
    estado           VARCHAR(32) DEFAULT 'PENDING',    -- PENDING, PROCESSING, COMPLETED, FAILED
    tipo_entrada     VARCHAR(16) DEFAULT 'TEXTO',      -- TEXTO, AUDIO
    texto_raw        TEXT,                             -- Texto original sin procesar
    fuente           VARCHAR(64) DEFAULT 'api'         -- 'dataset_osce', 'demo_streamlit', 'api'
);

-- ─────────────────────────────────────────────────────────────
-- predicciones
-- Resultado de clasificación Manchester para una entrevista.
-- Una entrevista puede tener una predicción por modelo ejecutado.
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS predicciones (
    guid_prediccion    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    guid_entrevista    UUID REFERENCES entrevistas(guid_entrevista) ON DELETE CASCADE,
    modelo_id          VARCHAR(64),                    -- nombre del modelo (e.g. 'logistic_regression')
    modelo_version     VARCHAR(32),                    -- versión del artefacto (e.g. '2026-05-14')
    nivel_predicho     VARCHAR(4),                     -- C1 / C2 / C3 / C4 / C5
    nivel_llm_sugerido VARCHAR(4),                     -- sugerencia del LLM (solo si participó en Phase 3)
    confianza          FLOAT,                          -- probabilidad de la clase predicha (0-1)
    safety_override    BOOLEAN DEFAULT FALSE,          -- True si las reglas hardcodeadas cambiaron el nivel
    nivel_final        VARCHAR(4),                     -- nivel después de aplicar safety_rules
    timestamp          TIMESTAMP DEFAULT NOW(),
    log_decisiones     JSONB DEFAULT '{}'::JSONB       -- trazabilidad detallada de la predicción
);

-- ─────────────────────────────────────────────────────────────
-- pipeline_runs
-- Log de ejecución de cada DAG run.
-- Se usa para auditoría, comparación de métricas y trazabilidad de artefactos.
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dag_id         VARCHAR(64),                        -- 'dag_training' o 'dag_inference'
    workflow_id    VARCHAR(128),                       -- Airflow run_id
    timestamp      TIMESTAMP DEFAULT NOW(),
    estado         VARCHAR(32) DEFAULT 'RUNNING',      -- RUNNING, SUCCESS, FAILED
    metricas       JSONB DEFAULT '{}'::JSONB,          -- métricas del run (accuracy, F1, etc.)
    artefacto_uri  VARCHAR(256)                        -- URI del artefacto en MinIO (e.g. 'minio://triageia-models/lr_v1.joblib')
);

-- Índices para consultas frecuentes
CREATE INDEX IF NOT EXISTS idx_entrevistas_estado ON entrevistas(estado);
CREATE INDEX IF NOT EXISTS idx_entrevistas_fuente ON entrevistas(fuente);
CREATE INDEX IF NOT EXISTS idx_predicciones_guid_entrevista ON predicciones(guid_entrevista);
CREATE INDEX IF NOT EXISTS idx_predicciones_modelo ON predicciones(modelo_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_dag ON pipeline_runs(dag_id);
