# TriageIA — Sistema Automático de Triaje Manchester con ML

> Herramienta de soporte a la decisión clínica que transforma texto clínico o voz del paciente en una prioridad médica estructurada.

---

## Descripción

TriageIA simula un sistema de triaje automático basado en el **Sistema Manchester de Triaje (MTS)**. A partir de texto clínico o audio transcrito, el sistema:

1. Extrae y normaliza síntomas mediante NLP
2. Clasifica el caso en uno de los 5 niveles de prioridad Manchester (C1-C5)
3. Explica la predicción con SHAP
4. Aplica reglas de seguridad clínica para detectar casos de alto riesgo
5. Registra todo el proceso con trazabilidad completa (GUID, timestamps, estados)

El objetivo principal **no es solo que funcione**, sino demostrar comprensión profunda de cada decisión de diseño: por qué se eligió cada modelo, qué métricas importan en un contexto clínico y cuáles son las limitaciones del sistema.

---

## Sistema Manchester

| Nivel | Color    | Tiempo máx. | Descripción |
|-------|----------|-------------|-------------|
| C1    | Rojo     | Inmediato   | Resucitación / intervención urgente |
| C2    | Naranja  | 10-15 min   | Emergencia |
| C3    | Amarillo | 60 min      | Urgencia |
| C4    | Verde    | 2 horas     | Urgencia menor |
| C5    | Morado   | 4 horas     | No urgente |

---

## Dataset

- **Fuente:** Diálogos médico-paciente transcritos (OSCE clínico, inglés)
- **Volumen:** 272 casos en `Dataset/text/text/`
- **Especialidades:** Respiratorio (RES=213), Musculoesquelético (MSK=46), Gastroenterológico (GAS=6), Cardiológico (CAR=5), Dermatológico (DER=1), General (GEN=1)
- **Etiquetas Manchester:** Asignadas en Phase 3 mediante LLM + revisión humana
- **Nota:** Distribución muy desbalanceada (RES=78%). Se documenta y trata explícitamente.

---

## Arquitectura de servicios

```
┌───────────────────────────────────────────────────────────────┐
│  Docker Compose (WSL2)                                         │
│                                                                │
│  ┌──────────────────┐    ┌─────────────────────────────────┐  │
│  │   Airflow :8080  │───▶│   Postgres :5432                │  │
│  │  (LocalExecutor) │    │  - Metastore Airflow            │  │
│  │  dag_training    │    │  - entrevistas (GUID, estados)  │  │
│  │  dag_inference   │    │  - predicciones                 │  │
│  └──────────────────┘    │  - pipeline_runs                │  │
│                          └─────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │   MinIO :9000 / consola :9001                           │  │
│  │  triageia-raw · triageia-processed · triageia-models    │  │
│  │  triageia-reports                                       │  │
│  └─────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────┘
```

**Etapa A — Entrenamiento** (`dag_training`):
```
load_raw_data → assign_manchester_labels → clean_and_ner
→ build_features → train_models → evaluate_compare → safety_audit
```

**Etapa B — Inferencia** (`dag_inference`):
```
receive_input → [transcribe_if_audio] → clean_text → extract_entities
→ build_features → predict → apply_safety_rules → store_result
```

---

## Pipeline de fases (desarrollo)

```
Phase 0  → ✅ Infraestructura base (estructura, dependencias, configuración)
Phase 1  → ✅ Exploración del dataset (EDA, análisis de distribución)
Phase 2  → ✅ Infraestructura de orquestación (Docker, Airflow, Postgres, MinIO)
Phase 3  → ✅ Ground truth Manchester (LLM + revisión)
Phase 4  → ⏳ Limpieza y NER
Phase 5  → ⏳ Ingeniería de features (TF-IDF, features estructuradas)
Phase 6  → ⏳ Pipeline de entrenamiento (DAG Airflow — Etapa A)
Phase 7  → ⏳ Evaluación y comparación de modelos
Phase 8  → ⏳ Reglas de seguridad clínica y auditoría de under-triage
Phase 9  → ⏳ Pipeline de inferencia (DAG Airflow — Etapa B)
Phase 10 → ⏳ Demo Streamlit (audio → Whisper → pipeline → predicción)
Phase 11 → ⏳ Documentación y defensa
```

---

## Estructura de carpetas

```
emergency_triage_system/
├── Dataset/              <- Dataset fuente (solo local, no en git)
│   ├── text/text/        <- 272 diálogos D:/P: (fuente para ML)
│   └── cleantext/        <- Formato ASR (referencia demo Whisper)
├── data/                 <- Datos procesados (no en git)
├── infra/                <- Infraestructura de servicios (en git)
│   ├── docker-compose.yml
│   ├── airflow/dags/     <- dag_training.py, dag_inference.py
│   ├── postgres/         <- init.sql (schema trazabilidad)
│   └── minio/            <- setup_buckets.sh
├── notebooks/            <- Análisis por fase
├── src/                  <- Código fuente modular
│   ├── preprocessing/    <- text_cleaner.py, normalizer.py
│   ├── extraction/       <- ner.py, llm_extractor.py
│   ├── features/         <- feature_builder.py
│   ├── models/           <- trainer.py, evaluator.py, safety_rules.py
│   ├── pipeline/         <- tasks.py por etapa (glue code para DAGs)
│   ├── traceability/     <- tracer.py (GUID/Postgres), storage.py (MinIO)
│   └── utils/            <- manchester.py
├── models/               <- Artefactos .joblib (solo local, no en git)
├── app/                  <- Demo Streamlit
├── reports/              <- Figuras y métricas para la presentación
└── docs/                 <- Decisiones y material de defensa
```

---

## Instalación

### Entorno de análisis y ML

```bash
# Crear entorno virtual
python -m venv .venv
source .venv/bin/activate      # Linux/WSL2
# .venv\Scripts\activate       # Windows CMD

# Instalar dependencias ML/NLP
pip install -r requirements.txt

# Modelo de spaCy en inglés
python -m spacy download en_core_web_sm
```

### Servicios de orquestación (Phase 2 — implementado)

```bash
# Copiar variables de entorno (añadir ANTHROPIC_API_KEY)
cp infra/.env.example infra/.env

# Levantar todos los servicios (primera vez: ~5 min descarga de imágenes)
docker compose -f infra/docker-compose.yml up -d

# Verificar estado
docker compose -f infra/docker-compose.yml ps

# Verificar Airflow (puede tardar 1-2 min)
curl http://localhost:8080/health

# Crear buckets en MinIO (requiere mc instalado)
bash infra/minio/setup_buckets.sh

# Verificar tablas de trazabilidad en Postgres
docker compose -f infra/docker-compose.yml exec postgres \
  psql -U triageia -d triageia_db -c "\dt"

# UIs disponibles:
# Airflow:  http://localhost:8080  (admin / admin)
# MinIO:    http://localhost:9001  (minioadmin / minioadmin)
```

---

## Modelos comparados

| Modelo | Justificación |
|--------|--------------|
| DummyClassifier | Baseline absoluto |
| Naive Bayes | Baseline probabilístico, interpretable, rápido |
| Logistic Regression | Lineal, funciona bien con TF-IDF, coeficientes explicables |
| LinearSVC | Robusto en alta dimensionalidad |
| Random Forest | Ensemble, maneja bien el ruido textual |
| XGBoost | Mejor rendimiento empírico en datos tabulares |

---

## Métricas clave

- **F1-macro** — trata todas las clases por igual (importante con desbalanceo)
- **Under-triage rate** — % de C1/C2 clasificados como C4/C5 (crítico para seguridad clínica)
- **Accuracy por clase** — detecta qué niveles se confunden más

---

## Limitaciones

- Dataset en inglés (no en español)
- Etiquetas Manchester asignadas semi-automáticamente (no validadas por clínico real)
- Volumen reducido (272 casos) — resultados exploratorios, no clínicamente validados
- **Este sistema no debe usarse en entornos clínicos reales sin validación médica**

---

## Contexto académico

Proyecto de curso de Machine Learning. La prioridad es la comprensión y justificación de cada decisión de diseño, no solo el rendimiento del modelo final.
