# TriageIA — Log de Decisiones

Registro cronológico de todas las decisiones relevantes del proyecto.
Cada entrada incluye: qué se decidió, por qué, alternativas descartadas y riesgos identificados.

---

## Fase 0 — Infraestructura Base (13/05/2026)

### D-001: Estructura de carpetas del proyecto

**Decisión:** Separar `data/` (outputs del pipeline, ignorados en git) de `Dataset/` (fuente original, solo local).

**Por qué:** Los datos procesados son reproducibles desde el código. Mantenerlos en git inflaría el repositorio y podría incluir datos sensibles accidentalmente. La fuente original tampoco se commitea para evitar subir datos sin control de licencia.

**Alternativas descartadas:**
- Todo en git: riesgo de repositorio pesado y datos sensibles.
- Todo ignorado: no se puede reproducir el pipeline sin instrucciones adicionales.

**Riesgo:** Si el Dataset/ local se pierde, no hay backup en el repositorio. Mitigación: documentar la fuente original del dataset en este log.

---

### D-002: Fuente del dataset — `text/text/` vs `cleantext/`

**Decisión:** Usar `Dataset/text/text/` como fuente principal para ML/NLP.

**Por qué:** Contiene casing correcto, puntuación natural y etiquetas de hablante `D:` (Doctor) y `P:` (Patient). Esto permite:
- Filtrar solo los turnos del paciente para el análisis de síntomas
- Aprovechar información sintáctica (puntuación, mayúsculas para nombres propios)
- Comparar directamente con la salida de Whisper (que también produce texto con casing)

**Alternativas descartadas:**
- `cleantext/`: Formato ASR (todo mayúsculas, sin puntuación). Diseñado para entrenar modelos de voz, no para NLP. Reduce la riqueza lingüística del texto.

**Uso de `cleantext/`:** Reservado como referencia para la demo final de audio (comparar formato Whisper vs. texto procesado).

**Riesgo:** Los 272 archivos de `text/text/` podrían tener variaciones de formato entre especialidades. Verificar en Fase 1.

---

### D-003: Archivos `.info` del dataset

**Decisión:** Mantener los 4 archivos `.info` para referencia, no usarlos en el pipeline de ML.

**Por qué:** Contienen alineamiento audio-texto (timestamps por utterance para archivos mp3 que no están disponibles localmente). Son útiles para:
- Entender la estructura del dataset original
- Preparar la demo de audio en Fase 10 (si se consiguen los audios)

**Alternativas descartadas:**
- Ignorarlos completamente: podrían ser útiles para la demo y muestran la procedencia del dataset.

---

### D-004: Gestión del dataset en git

**Decisión:** `Dataset/` ignorado en git (`.gitignore`). Solo existe localmente.

**Por qué:** El usuario explícitamente solicitó que el dataset no esté en git. Razones adicionales: tamaño (~3.5 MB), posibles restricciones de licencia, y convención de no versionar datos en repos de ML.

**Alternativas descartadas:**
- Mantener dataset en git: más fácil de compartir pero viola convenciones ML y puede generar problemas de tamaño/licencia.

**Riesgo:** Pérdida de datos si el equipo local falla. Mitigación: documentar la fuente original.

**Fuente original del dataset:** Dataset de diálogos médico-paciente OSCE/clínicos (inglés). Formato de transcripción con speaker labels D:/P:. 272 casos. Especialidades: RES, MSK, GAS, CAR, DER, GEN.

---

### D-005: Gestión de `.claude/` en git

**Decisión:** `.claude/*` ignorado en git (añadido por el usuario al `.gitignore`).

**Por qué:** Contiene configuración local (settings.local.json) y skills del proyecto que son específicas del entorno de desarrollo local. Las skills se mantienen localmente y se documentan en CLAUDE.md para poder recrearlas si es necesario.

**Impacto:** Las 7 skills creadas (`triageia-context`, `triageia-phase`, etc.) son solo locales. Si se clona el repositorio en otra máquina, deben recrearse manualmente.

---

### D-006: Skills del proyecto

**Decisión:** Crear 7 skills en `.claude/skills/` para el proyecto.

**Por qué:** Reducen la repetición de contexto entre conversaciones, sirven como guías metodológicas invocables y refuerzan las reglas del proyecto sin depender de que CLAUDE.md esté cargado. Son distintas a CLAUDE.md en que pueden invocarse explícitamente con `/triageia-<nombre>`.

**Skills creadas:**
| Skill | Tipo de invocación | Propósito principal |
|-------|-------------------|---------------------|
| `triageia-context` | background (auto) | Contexto global persistente |
| `triageia-phase` | usuario (`/triageia-phase`) | Protocolo de justificación antes de cada fase |
| `triageia-data` | ambos | Checklist de exploración y etiquetado |
| `triageia-llm-labeling` | ambos | Uso responsable del LLM |
| `triageia-ml-modeling` | ambos | Entrenamiento y comparación sistemática |
| `triageia-safety-audit` | usuario | Auditoría de under-triage |
| `triageia-defense` | usuario | Checklist de defensa y documentación |

**Alternativas descartadas:**
- Solo CLAUDE.md: no invocable por nombre, menos estructurado.
- Usar skill-creator con eval loop: innecesario para guías metodológicas.

**Riesgo:** Skills solo locales. Si se pierde `.claude/`, deben recrearse. El contenido está documentado en el plan: `C:\Users\MARCOS\.claude\plans\act-a-como-arquitecto-t-cnico-keen-twilight.md`.

---

### D-007: requirements.txt — dependencias iniciales

**Decisión:** Incluir dependencias desde el inicio agrupadas por función.

**Dependencias clave y justificación:**
- `imbalanced-learn`: para SMOTE (desbalanceo RES=78%)
- `anthropic`: LLM para extracción/normalización (no clasificación)
- `openai-whisper`: transcripción audio para demo final
- `shap`: explicabilidad del modelo (requerida en demo Streamlit)
- `xgboost`: mejor rendimiento empírico en tabular, incluido por comparación

**Riesgo:** `openai-whisper` requiere `ffmpeg` instalado en el sistema. `shap` puede dar conflictos con versiones de numpy. Verificar al instalar.

---

## Fase 1 — Exploración del Dataset (13/05/2026)

### D-008: Representación textual — diálogo completo vs. solo paciente

**Decisión:** Usar `texto_dialogo_completo` como baseline principal. Conservar `texto_paciente` para comparación en Fase 7.

**Por qué:** Coherencia entrenamiento-inferencia. Whisper no aplica diarización: la app Streamlit recibirá el audio completo transcrito como bloque sin separación de hablantes. Entrenar con solo P: y evaluar con texto completo crearía un shift de distribución no documentado.

**Alternativas descartadas:**
- Solo texto_paciente: más limpio semánticamente pero inconsistente con la inferencia real.
- Solo turno inicial P:: pierde información de respuestas posteriores.
- NER → síntomas: requiere Fase 4, no disponible aún.

**Riesgo:** Potencial leakage diagnóstico por preguntas del doctor. Mitigación: comparar explícitamente ambas representaciones en Fase 7.

**Referencia:** `docs/decisions/01_dataset_text_representation.md`

---

### D-009: Anomalías de formato detectadas en el EDA

**Hallazgos:**
- 4 archivos usan `D;` en lugar de `D:` (CAR0001, CAR0002, RES0079, RES0194). Typo tipográfico. Parser resuelto con regex `[DP][;:]`.
- 2 archivos en UTF-16 LE con BOM (RES0002, RES0054). Parser actualizado para intentar utf-8 → utf-16 → latin-1.
- **Resultado: 272/272 archivos parsean correctamente.** No hay archivos vacíos ni sin turnos.

---

### D-010: Estadísticas del dataset (Fase 1)

| Métrica | Valor |
|---------|-------|
| Total de casos | 272 |
| Distribución | RES=213 (78.3%), MSK=46 (16.9%), GAS=6, CAR=5, DER=1, GEN=1 |
| Longitud media diálogo completo | 7.183 chars |
| Longitud media texto paciente | 2.860 chars (~40% del total) |
| Turnos P: por caso (rango) | 22–78 |

---

## Decisiones Pendientes (para Fase 2)

| ID | Decisión | Fase |
|----|---------|------|
| P-001 | ¿Cómo asignar niveles Manchester? (mapeo / LLM / combinado) | Fase 2 |
| P-003 | ¿Cómo tratar el desbalanceo RES=78%? (class_weight / SMOTE / submuestreo) | Fase 6-7 |
| P-004 | ¿Estrategia de train/val/test dado el tamaño reducido (272 casos)? | Fase 7 |

*P-002 resuelta en D-008: se usa diálogo completo como baseline principal.*

---

## Próximos pasos confirmados

1. Invocar `/triageia-phase fase-2` para iniciar el protocolo de la Fase 2
2. Fase 2: Decidir estrategia de asignación de niveles Manchester (P-001)
3. Fase 2: Construir `data/master/dataset_maestro.csv` con columna `nivel_manchester`
4. Crear `docs/decisions/02_ground_truth.md`
