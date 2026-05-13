# D-Fase1-001: Representación textual del dataset

**Fase:** 1 — Exploración del dataset  
**Fecha:** 13/05/2026  
**Estado:** Decidido

---

## Contexto

El dataset contiene 272 diálogos médico-paciente en formato `D:` / `P:`. Cada archivo produce tres representaciones distintas del mismo caso:

| Representación | Descripción |
|----------------|-------------|
| `texto_dialogo_completo` | Diálogo D:/P: completo |
| `texto_paciente` | Solo turnos `P:` concatenados |
| `texto_doctor` | Solo turnos `D:` (referencia analítica) |

---

## Estadísticas del EDA (Fase 1)

| Métrica | Valor |
|---------|-------|
| Total de casos | 272 |
| Longitud media — diálogo completo | 7.183 chars |
| Longitud media — solo paciente | 2.860 chars |
| Ratio paciente/total promedio | ~40% |
| Turnos paciente por caso (rango) | 22–78 |

---

## Alternativas evaluadas

### Opción A — Solo turnos P:
**Ventaja:** Elimina ruido de las preguntas del doctor.  
**Desventaja crítica:** Mismatch con la inferencia real. Whisper no aplica diarización: la app final recibirá el diálogo completo transcrito. Entrenar con solo P: y evaluar con texto completo crea un shift de distribución no documentado.

### Opción B — Diálogo completo D:+P:
**Ventaja:** Coherente con la condición real de inferencia. Incluye vocabulario clínico contextual.  
**Desventaja:** Potencial leakage diagnóstico: las preguntas del doctor revelan su hipótesis clínica. Riesgo documentado y medido en Fase 7.

### Opción C — Solo turno inicial P:
**Desventaja:** Pierde información de respuestas posteriores donde emergen síntomas relevantes.

### Opción D — Síntomas extraídos por NER
**Desventaja:** Requiere el pipeline NER de Fase 4, no disponible aún.

---

## Decisión: enfoque híbrido escalonado

1. **`texto_dialogo_completo` como baseline principal** (Fases 6–7)
2. **`texto_paciente` como alternativa a comparar** en Fase 7
3. **`texto_doctor` conservado** en el CSV para referencia, no para entrenamiento

El CSV conserva las tres columnas, lo que permite cambiar representación sin re-parsear.

---

## Justificación

**Coherencia entrenamiento-inferencia** es el criterio decisivo.

Whisper no implementa diarización por defecto. La app Streamlit recibirá el audio completo de la consulta y lo transcribirá en bloque. El clasificador en producción verá texto sin etiquetar por hablante. Entrenar con `texto_paciente` y evaluar con texto completo haría los resultados de validación engañosos.

---

## Riesgos

| Riesgo | Mitigación |
|--------|------------|
| Leakage por preguntas del doctor | Comparar diálogo_completo vs. solo_paciente en Fase 7 y documentar diferencia de métricas |
| Varianza por longitud (RES más largo) | `sublinear_tf=True` en TF-IDF (Fase 6); analizar correlación longitud/predicción |

---

## Anomalías de formato detectadas

| Archivo | Problema | Impacto |
|---------|---------|---------|
| CAR0001, CAR0002, RES0079, RES0194 | `D;` en lugar de `D:` (typo) | Ninguno — parser lo maneja con regex `[DP][;:]` |
| RES0002, RES0054 | Codificación UTF-16 LE con BOM | Ninguno — parser detecta y re-intenta con utf-16 |

**No hay archivos vacíos, duplicados ni sin turnos en el dataset.**

---

## Evidencias

- `data/processed/dataset_exploracion_fase1.csv` — 272 filas, 12 columnas
- `reports/figures/distribucion_grupos_clinicos.png` — **CAPTURA PARA PRESENTACIÓN**
- `notebooks/01_eda.ipynb` — análisis interactivo reproducible
- `src/eda_fase1.py` — script reproducible

---

## Pendiente (Fase 2)

- Asignar niveles Manchester → decisión P-001
- Construir `data/master/dataset_maestro.csv` con columna `nivel_manchester`
