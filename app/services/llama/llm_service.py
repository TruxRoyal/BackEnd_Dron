import requests
import json
from typing import Any, Dict

class LLMService:
    def __init__(self, model: str = "llama3", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url.rstrip("/")

    def explain_analysis(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        # --- Contexto del rol del modelo ---
        system_prompt = (
            "Eres un ingeniero agrónomo especializado en cultivos de fresa en clima andino. "
            "Tu tarea es interpretar los resultados de un análisis de imagen del cultivo y generar un informe técnico breve, "
            "con tono profesional pero entendible para productores agrícolas. "
            "Debes analizar indicadores como cobertura foliar, índices de vegetación, madurez de frutos, nitidez de la imagen y presencia de manchas en hojas. "
            "Identifica posibles problemas fisiológicos o sanitarios, y sugiere recomendaciones prácticas de manejo (riego, nutrición, control biológico, manejo del suelo, etc.). "
            "Evita repetir las métricas numéricas literalmente: interprétalas en lenguaje natural y destaca conclusiones útiles."
        )

        # --- Estructura del mensaje enviado al modelo ---
        prompt = f"""<|system|>\n{system_prompt}\n<|end|>\n
<|user|>\nAnaliza los siguientes datos obtenidos por visión artificial del cultivo de fresa:\n
{json.dumps(metrics, indent=2, ensure_ascii=False)}\n
Por favor genera un texto con la siguiente estructura:
1. **Resumen general del estado del cultivo**
2. **Interpretación de los resultados clave**
3. **Posibles causas o factores agronómicos**
4. **Recomendaciones técnicas concretas**
5. **Conclusión final**\n
Usa un tono claro, técnico y natural, evitando listas excesivas o frases genéricas.\n<|end|>
"""

        body = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.3,
                "num_predict": 512
            }
        }

        try:
            response = requests.post(f"{self.base_url}/api/generate", json=body, timeout=90)
            response.raise_for_status()
            content = response.json()
            return {
                "success": True,
                "response": content.get("response", "").strip()
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
