import json
import urllib.request
import urllib.error
from typing import Optional

from utils import fmt_cop


OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen2.5:3b"

SYSTEM_BASE = (
    "Eres el asistente de inteligencia artificial de Pacioli, una app de presupuesto personal mensual.\n"
    "Moneda: pesos colombianos (COP). Usa el formato $XXX.XXX (punto como separador de miles, sin decimales).\n"
    "Contexto: el usuario controla sus finanzas personales, ingresos y gastos mensuales.\n"
    "Responde siempre en español, sé directo, breve y práctico.\n"
    "Nunca inventes datos que no se te den. Si no tienes información, dilo."
)

CORRECTION_KEYWORDS = [
    'no', 'equivocado', 'incorrecto', 'mal', 'error', 'estás mal',
    'eso no es', 'te equivocas', 'en realidad', 'de hecho',
    'corrección', 'corregir', 'en realidad es', 'no es así',
    'mejor', 'prefiero', 'así no', 'cámbialo'
]


def _call_ollama(prompt: str, system: str = "", timeout: int = 30) -> Optional[str]:
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.7, "num_predict": 400}
    }
    sys_msg = SYSTEM_BASE
    if system:
        sys_msg += "\n\n" + system
    payload["system"] = sys_msg
    try:
        req = urllib.request.Request(
            OLLAMA_URL,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
            return data.get("response", "").strip()
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return None


def detect_correction(user_message: str) -> bool:
    msg = user_message.lower()
    return any(kw in msg for kw in CORRECTION_KEYWORDS)


def extract_correction_topic(user_message: str) -> str:
    msg = user_message.lower()
    topics = {
        'gasto': 'gastos', 'gastos': 'gastos', 'comida': 'alimentación',
        'alimentación': 'alimentación', 'servicios': 'servicios',
        'transporte': 'transporte', 'salud': 'salud', 'educación': 'educación',
        'vivienda': 'vivienda', 'ahorro': 'ahorro', 'presupuesto': 'presupuesto',
        'ingreso': 'ingresos', 'ingresos': 'ingresos', 'deuda': 'deudas',
        'deudas': 'deudas', 'inversión': 'inversiones', 'inversiones': 'inversiones',
    }
    for kw, topic in topics.items():
        if kw in msg:
            return topic
    return 'general'


def generate_description(category: str, subcategory: str, amount: float,
                         desc_learnings_ctx: str = "") -> Optional[str]:
    prompt = (
        f"Genera una descripción breve y útil para un gasto de {fmt_cop(amount)} en la categoría '{category}'"
        + (f", subcategoría '{subcategory}'" if subcategory else "")
        + ". Solo devuelve la descripción, nada más. Máximo 8 palabras."
    )
    if desc_learnings_ctx:
        prompt = desc_learnings_ctx + "\n\n" + prompt + "\n\nSigue el estilo de las correcciones anteriores."
    return _call_ollama(prompt, system="Responde solo con la descripción. Nada más.")


def analyze_spending(month_name: str, data: list, total_expense: float, total_income: float,
                     learnings_ctx: str = "") -> Optional[str]:
    lines = []
    for d in data:
        lines.append(f"- {d['name']}: {fmt_cop(d['actual'])} / {fmt_cop(d['budget'])} presupuesto ({d['percent']:.0f}%)")
    budget_text = "\n".join(lines) if lines else "No hay presupuestos definidos."

    prompt = (
        f"Analiza los gastos de {month_name}:\n"
        f"Ingresos: {fmt_cop(total_income)}\nGastos totales: {fmt_cop(total_expense)}\n"
        f"Balance: {fmt_cop(total_income - total_expense)}\n\n"
        f"Desglose por categoría:\n{budget_text}\n\n"
    )
    if learnings_ctx:
        prompt += f"\n{learnings_ctx}\n\n"
    prompt += "Da 3 consejos concretos para ahorrar basándote en estos datos reales.\nSé directo y práctico. Máximo 5 líneas."

    return _call_ollama(prompt, system="Eres un asesor financiero personal. Analiza datos reales, no des tips genéricos.")


def ask_budget_question(question: str, context: str = "",
                        chat_history: str = "", learnings_ctx: str = "") -> Optional[str]:
    prompt = ""
    if learnings_ctx:
        prompt += f"{learnings_ctx}\n\n"
    if chat_history:
        prompt += f"Conversación reciente:\n{chat_history}\n\n"
    prompt += f"Pregunta del usuario: {question}"
    if context:
        prompt += f"\n\nDatos del mes actual:\n{context}"

    return _call_ollama(prompt, system="Responde preguntas sobre las finanzas personales del usuario. Usa los datos que te den. Si el usuario te corrige, recuerda esa corrección para futuro.")
