# TriageIA — Sistema Automático de Triaje Manchester con ML

> Herramienta de soporte a la decisión clínica que transforma la voz del paciente en una prioridad médica estructurada.

---

## Descripción

TriageIA simula un sistema de triaje automático basado en el **Sistema Manchester de Triaje (MTS)**. A partir de texto clínico o audio transcrito, el sistema:

1. Extrae y normaliza síntomas mediante NLP
2. Clasifica el caso en uno de los 5 niveles de prioridad Manchester (C1-C5)
3. Explica la predicción con SHAP
4. Aplica reglas de seguridad clínica para detectar casos de alto riesgo

El objetivo principal **no es solo que funcione**, sino demostrar comprensión profunda de cada decisión de diseño: por qué se eligió cada modelo, qué métricas importan en un contexto clínico y cuáles son las limitaciones del sistema.

---

## Sistema Manchester

| Nivel | Color   | Tiempo máx. | Descripción |
|-------|---------|-------------|-------------|
| C1    | Rojo    | Inmediato   | Resucitación / intervención urgente |
| C2    | Naranja | 10-15 min   | Emergencia |
| C3    | Amarillo| 60 min      | Urgencia |
| C4    | Verde   | 2 horas     | Urgencia menor |
| C5    | Morado  | 4 horas     | No urgente |

---

## Dataset

- **Fuente:** Diálogos médico-paciente transcritos (OSCE clínico, inglés)
- **Volumen:** 272 casos en `Dataset/cleantext/`
- **Especialidades:** Respiratorio (RES), Musculoesquelético (MSK), Gastroenterológico (GAS), Cardiológico (CAR), Dermatológico (DER), General (GEN)
- **Etiquetas Manchester:** Generadas en Fase 2 mediante mapeo especialidad + análisis de contenido
- **Nota:** Distribución muy desbalanceada (RES=78%). Se documenta y trata en la Fase 6-7.

---

## Pipeline de fases

```
Fase 0  → Infraestructura base (estructura, dependencias, configuración)
Fase 1  → Exploración del dataset (EDA, análisis de distribución)
Fase 2  → Construcción del dataset maestro (labels Manchester)
Fase 3  → Limpieza y normalización textual
Fase 4  → Extracción de entidades clínicas (NER)
Fase 5  → Normalización de síntomas
Fase 6  → Ingeniería de features (TF-IDF, features binarias)
Fase 7  → Entrenamiento de modelos (NB, LR, SVM, RF, XGBoost)
Fase 8  → Comparación de métricas y selección del mejor modelo
Fase 9  → Auditoría de seguridad clínica (under-triage)
Fase 10 → Aplicación Streamlit (audio → transcripción → predicción)
Fase 11 → Documentación y defensa
```

---

## Estructura de carpetas

```
emergency_triage_system/
├── Dataset/          <- Dataset fuente (diálogos clínicos)
│   ├── cleantext/    <- 272 transcripciones limpias
│   └── *.info        <- Alineamiento audio-texto
├── data/             <- Datos procesados (generados, no en git)
├── notebooks/        <- Análisis exploratorio y experimentos por fase
├── src/              <- Código fuente modular
│   ├── preprocessing/
│   ├── extraction/
│   ├── features/
│   ├── models/
│   └── utils/
├── models/           <- Modelos entrenados serializados
├── reports/          <- Figuras, métricas y registros de decisiones
├── app/              <- Demo Streamlit
└── docs/             <- Documentación de decisiones y defensa
```

---

## Instalación

```bash
# Crear entorno virtual
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/Mac

# Instalar dependencias
pip install -r requirements.txt

# Modelo de spaCy en inglés
python -m spacy download en_core_web_sm
```

---

## Ejecución

```bash
# Exploración (Fase 1)
jupyter lab notebooks/01_eda.ipynb

# Demo Streamlit (Fase 10)
streamlit run app/streamlit_app.py
```

---

## Modelos comparados

| Modelo | Justificación |
|--------|--------------|
| Naive Bayes | Baseline probabilístico, interpretable, rápido |
| Logistic Regression | Lineal, funciona bien con TF-IDF, coeficientes explicables |
| SVM | Robusto en espacios de alta dimensionalidad |
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
