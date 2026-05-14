"""
LLM-based Manchester level suggester (Phase 3 — Ground Truth).

Usage: ONLY for building the training dataset (Phases 3-4).
       NOT used in production inference — that uses the trained ML model.

Model: claude-haiku-4-5-20251001 (cost-efficient for batch processing 272 cases)
Temperature: 0.1 (reproducibility)
Input: texto_paciente (patient turns only, to minimize doctor contamination)
Output: {sintomas, nivel_sugerido, razon, confianza}
"""

import json
import os
import time

import anthropic

# ─── Prompt ──────────────────────────────────────────────────────────────────

MANCHESTER_SYSTEM_PROMPT = """You are a clinical triage assistant trained in the Manchester Triage System (MTS).
Your task is to suggest a Manchester priority level (C1-C5) based on the patient's statements during a clinical interview.

Manchester levels:
- C1 (Red / Immediate): Resuscitation needed. Life-threatening symptoms: unconscious, no breathing, severe hemorrhage, anaphylaxis.
- C2 (Orange / 10-15 min): Emergency. Severe pain (>7/10), altered consciousness, difficulty breathing, chest pain, suspected stroke.
- C3 (Yellow / 60 min): Urgent. Moderate pain (4-7/10), fever >38.5°C with other symptoms, vomiting+diarrhea >24h, acute infection.
- C4 (Green / 2h): Minor urgent. Mild symptoms, pain <4/10, musculoskeletal injury without deformity, mild rash.
- C5 (Purple / 4h): Non-urgent. Chronic conditions, administrative follow-up, very mild symptoms.

Rules:
1. ONLY analyze what the patient explicitly states. Do not assume information not mentioned.
2. When in doubt between two levels, assign the more urgent one (triage safety principle).
3. Respond ONLY with a valid JSON object — no markdown, no explanation outside the JSON.

Required JSON format:
{
  "sintomas": ["symptom 1", "symptom 2"],
  "nivel_sugerido": "C3",
  "razon": "Brief clinical justification (max 2 sentences)",
  "confianza": 0.75
}

confianza must be between 0.0 and 1.0.
nivel_sugerido must be exactly one of: C1, C2, C3, C4, C5.
"""

MANCHESTER_USER_TEMPLATE = """Analyze the following patient statements and suggest a Manchester triage level.

PATIENT STATEMENTS:
{texto_paciente}

Respond with a JSON object as specified."""

# ─── Client ──────────────────────────────────────────────────────────────────

def _get_client() -> anthropic.Anthropic:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY not set in environment")
    return anthropic.Anthropic(api_key=api_key)


# ─── Core function ───────────────────────────────────────────────────────────

def extraer_manchester(
    texto_paciente: str,
    model: str = "claude-haiku-4-5-20251001",
    temperatura: float = 0.1,
    max_retries: int = 3,
    delay_entre_reintentos: float = 2.0,
) -> dict:
    """
    Call Claude to suggest a Manchester level for one patient text.

    Returns dict with keys: sintomas, nivel_sugerido, razon, confianza.
    On failure returns a fallback dict with nivel_sugerido=None.
    """
    client = _get_client()

    user_msg = MANCHESTER_USER_TEMPLATE.format(texto_paciente=texto_paciente[:4000])

    for intento in range(1, max_retries + 1):
        try:
            response = client.messages.create(
                model=model,
                max_tokens=512,
                temperature=temperatura,
                system=MANCHESTER_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_msg}],
            )
            raw = response.content[0].text.strip()

            # Strip markdown code fences if present
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
                raw = raw.strip()

            resultado = json.loads(raw)

            # Validate required keys
            for key in ("sintomas", "nivel_sugerido", "razon", "confianza"):
                if key not in resultado:
                    raise ValueError(f"Missing key '{key}' in LLM response")

            # Validate nivel_sugerido
            if resultado["nivel_sugerido"] not in ("C1", "C2", "C3", "C4", "C5"):
                raise ValueError(f"Invalid nivel_sugerido: {resultado['nivel_sugerido']}")

            # Clamp confianza
            resultado["confianza"] = max(0.0, min(1.0, float(resultado["confianza"])))

            return resultado

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            if intento < max_retries:
                time.sleep(delay_entre_reintentos)
            else:
                return _fallback(str(e))

        except anthropic.APIError as e:
            if intento < max_retries:
                time.sleep(delay_entre_reintentos * intento)
            else:
                return _fallback(f"API error: {e}")

    return _fallback("Max retries reached")


def _fallback(motivo: str) -> dict:
    return {
        "sintomas": [],
        "nivel_sugerido": None,
        "razon": f"LLM extraction failed: {motivo}",
        "confianza": 0.0,
    }


# ─── Batch helper ────────────────────────────────────────────────────────────

def extraer_manchester_batch(
    textos: list[str],
    delay_entre_casos: float = 0.5,
    verbose: bool = True,
) -> list[dict]:
    """
    Process a list of patient texts. Returns one result dict per input.
    Adds a small delay between calls to respect rate limits.
    """
    resultados = []
    total = len(textos)
    for i, texto in enumerate(textos, 1):
        resultado = extraer_manchester(texto)
        resultados.append(resultado)
        if verbose:
            nivel = resultado.get("nivel_sugerido", "ERROR")
            conf = resultado.get("confianza", 0.0)
            print(f"  [{i:3d}/{total}] nivel={nivel}  conf={conf:.2f}")
        if i < total:
            time.sleep(delay_entre_casos)
    return resultados
