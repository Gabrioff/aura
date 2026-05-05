import os
import aiohttp
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.enums import ParseMode
import base64

# --- SISTEMA DE OFUSCACIÓN COMO RESPALDO ---
_T_CHUNKS = ["MUxUOA==", "LS1HR3hT", "MlVFMjRP", "YTlzb054", "bVBpYURs", "QUdONDlQ", "NDAwNDpB", "ODcwMDk3"]
_H_CHUNKS = ["QQ==", "dVJmS0xQ", "QU5KRUdO", "VXBqU1Jo", "SFl4TXpx", "QnlyVUhR", "aGZfb1BW"]

B64_TELEGRAM_TOKEN = "".join(reversed(_T_CHUNKS))
B64_HF_TOKEN = "".join(reversed(_H_CHUNKS))

# Decodificamos los tokens antiguos por si acaso
FALLBACK_TG = base64.b64decode(B64_TELEGRAM_TOKEN).decode("utf-8")
FALLBACK_HF = base64.b64decode(B64_HF_TOKEN).decode("utf-8")

# SOLUCIÓN: Le decimos a Python que use PRIMERO las variables de entorno de Render.
# Si no las encuentra (o fallan), intentará usar el código ofuscado.
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_TOKEN", FALLBACK_TG)
HF_TOKEN = os.getenv("HF_TOKEN", FALLBACK_HF)
AI_API_URL = os.getenv("AI_API_URL", "https://pepeoff-aura.hf.space/ask_ai")

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

class MarketAnalyzer:
    @staticmethod
    async def get_binance_data(symbol="SOLUSDT"):
        url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}"
        async with aiohttp.ClientSession() as session_binance:
            async with session_binance.get(url) as response:
                if response.status == 200:
                    return await response.json()
                return None

    @staticmethod
    def calculate_math_indicators(data):
        high = float(data['highPrice'])
        low = float(data['lowPrice'])
        close = float(data['lastPrice'])
        
        volatility_pct = ((high - low) / low) * 100
        pivot = (high + low + close) / 3
        r1 = (2 * pivot) - low
        s1 = (2 * pivot) - high
        
        price_change = float(data['priceChangePercent'])
        trend_strength = "Fuerte" if abs(price_change) > 5 else ("Moderada" if abs(price_change) > 2 else "Débil")

        return {
            "volatilidad_24h": round(volatility_pct, 2),
            "punto_pivote": round(pivot, 4),
            "resistencia_1": round(r1, 4),
            "soporte_1": round(s1, 4),
            "fuerza_tendencia": trend_strength
        }

async def fetch_ai_analysis(prompt_text: str) -> str:
    # INYECTAMOS EL TOKEN DE HUGGING FACE EN LOS HEADERS
    headers = {
        "Authorization": f"Bearer {HF_TOKEN}",
        "Content-Type": "application/json"
    }
    
    async with aiohttp.ClientSession(headers=headers) as session_api:
        try:
            async with session_api.post(AI_API_URL, json={"prompt": prompt_text}, timeout=120) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("response", "Error extrayendo respuesta.")
                elif response.status == 429:
                    return "⏳ La IA está ocupada procesando otras peticiones. Intenta de nuevo."
                elif response.status == 401:
                    return "❌ Acceso denegado: El token de Hugging Face es inválido o caducó."
                else:
                    error_data = await response.text()
                    return f"❌ Error de la IA (HTTP {response.status}): {error_data}"
        except Exception as e:
            return f"❌ No se pudo conectar al servidor de la IA. Error: {e}"

@dp.message(Command("start"))
async def send_welcome(message: types.Message):
    await message.answer(
        "🤖 *Dark Analyst V2*\n"
        "Escribe `/analizar BTCUSDT` o cualquier par de Binance.",
        parse_mode=ParseMode.MARKDOWN
    )

@dp.message(Command("analizar"))
async def analyze_crypto(message: types.Message):
    args = message.text.split()
    symbol = "SOLUSDT" if len(args) == 1 else args[1].upper()

    status_msg = await message.answer(f"🔄 **1.** Extrayendo datos de Binance para {symbol}...", parse_mode=ParseMode.MARKDOWN)

    api_data = await MarketAnalyzer.get_binance_data(symbol)
    if not api_data:
        return await status_msg.edit_text(f"❌ Error al obtener {symbol}. Verifica el nombre.")

    math_data = MarketAnalyzer.calculate_math_indicators(api_data)

    await status_msg.edit_text("🧠 **2.** Compilando algoritmos matemáticos y enviando a la IA...", parse_mode=ParseMode.MARKDOWN)

    ai_prompt = f"""
    Actúa como un trader institucional. Analiza esto para {symbol}:
    Precio: {api_data['lastPrice']} | Cambio: {api_data['priceChangePercent']}%
    Volatilidad: {math_data['volatilidad_24h']}% | Tendencia: {math_data['fuerza_tendencia']}
    Pivote: {math_data['punto_pivote']} | Soporte: {math_data['soporte_1']} | Resistencia: {math_data['resistencia_1']}

    Dame un análisis táctico en 3 párrafos:
    1. Acción del precio y volatilidad.
    2. Niveles clave y pivotes.
    3. Conclusión (Alcista/Bajista) con gestión de riesgo.
    """

    ai_response = await fetch_ai_analysis(ai_prompt)

    final_report = (
        f"📊 **REPORTE: {symbol}**\n\n"
        f"💰 *Precio:* {api_data['lastPrice']} ({api_data['priceChangePercent']}%)\n"
        f"🎯 *Pivote:* {math_data['punto_pivote']}\n"
        f"🛡️ *Sup:* {math_data['soporte_1']} | ⚔️ *Res:* {math_data['resistencia_1']}\n\n"
        f"🧠 **ANÁLISIS INSTITUCIONAL:**\n{ai_response}"
    )

    if len(final_report) > 4000:
        final_report = final_report[:4000] + "..."

    await status_msg.edit_text(final_report, parse_mode=ParseMode.MARKDOWN)

async def main():
    print("Iniciando polling de Telegram...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    print("Iniciando Bot de Telegram...")
    asyncio.run(main())