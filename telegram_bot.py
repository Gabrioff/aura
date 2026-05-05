import os
import aiohttp
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.enums import ParseMode

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")
AI_API_URL = os.getenv("AI_API_URL", "https://pepeoff-aura.hf.space/ask_ai")

# La base de la URL para hacer las consultas del balance
API_BASE_URL = AI_API_URL.replace("/ask_ai", "")

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("❌ ERROR CRÍTICO: No se encontró TELEGRAM_TOKEN.")
if not HF_TOKEN:
    print("⚠️ ADVERTENCIA: No se encontró HF_TOKEN.")

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

async def fetch_api_data(endpoint: str, method: str = "GET", payload: dict = None) -> dict:
    """Función maestra para comunicarse con Hugging Face usando el Token seguro"""
    headers = {
        "Authorization": f"Bearer {HF_TOKEN}",
        "Content-Type": "application/json"
    }
    url = f"{API_BASE_URL}{endpoint}"
    
    async with aiohttp.ClientSession(headers=headers) as session:
        try:
            if method == "POST":
                async with session.post(url, json=payload, timeout=120) as response:
                    return {"status": response.status, "data": await response.json() if response.status == 200 else await response.text()}
            else:
                async with session.get(url, timeout=30) as response:
                    return {"status": response.status, "data": await response.json() if response.status == 200 else await response.text()}
        except Exception as e:
            return {"status": 500, "data": str(e)}

@dp.message(Command("start"))
async def send_welcome(message: types.Message):
    # Registramos o leemos al usuario silenciosamente
    await fetch_api_data(f"/balance/{message.from_user.id}")
    
    await message.answer(
        "🤖 *Dark Analyst V2*\n"
        "Comandos disponibles:\n"
        "🔹 `/p <moneda>` - Analizar. Ejemplo: `/p sol` o `/p btcusdt`\n"
        "🔹 `/balance` - Ver tus fondos demo disponibles.",
        parse_mode=ParseMode.MARKDOWN
    )

@dp.message(Command("balance"))
async def check_balance(message: types.Message):
    user_id = message.from_user.id
    
    # Extraemos el balance desde la base de datos central en HF
    response = await fetch_api_data(f"/balance/{user_id}")
    balance = 0.00
    if response["status"] == 200:
        balance = response["data"].get("balance", 0.00)

    await message.answer(
        f"💼 **CUENTA DEMO**\n\n"
        f"💰 *Balance disponible:* `${balance:.2f} USD`\n\n"
        f"_(Los fondos son simulados y almacenados en el cerebro de la IA)_",
        parse_mode=ParseMode.MARKDOWN
    )

@dp.message(Command("p"))
async def analyze_crypto(message: types.Message):
    args = message.text.split()
    
    # Autocompletado inteligente de la moneda
    if len(args) == 1:
        symbol = "SOLUSDT"
    else:
        symbol = args[1].upper()
        if not symbol.endswith("USDT") and not symbol.endswith("USD"):
            symbol += "USDT"

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

    # Hacemos la petición a la IA mediante nuestra función maestra
    ai_resp = await fetch_api_data("/ask_ai", method="POST", payload={"prompt": ai_prompt})
    
    if ai_resp["status"] == 200:
        ai_response = ai_resp["data"].get("response", "Error extrayendo texto.")
    elif ai_resp["status"] == 429:
        ai_response = "⏳ La IA está ocupada procesando otras peticiones. Intenta de nuevo en unos segundos."
    else:
        ai_response = f"❌ Error de servidor (HTTP {ai_resp['status']}): {ai_resp['data']}"

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

# --- SERVIDOR WEB DUMMY PARA EVITAR EL ERROR DE RENDER ---
async def handle_ping(request):
    return web.Response(text="Bot de Telegram activo y funcionando.")

async def init_web_server():
    app = web.Application()
    app.router.add_get('/', handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    
    # Render asigna el puerto dinámicamente en la variable PORT (usualmente 10000)
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"✅ Servidor web de respaldo iniciado en el puerto {port}")

async def main():
    # 1. Iniciamos el servidor web falso para que Render detecte el puerto y no reinicie la app
    await init_web_server()
    
    print("Iniciando polling de Telegram...")
    # 2. Obligamos a Telegram a olvidar las instancias "fantasma" que se quedaron pegadas en el bucle
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    print("Iniciando Bot de Telegram...")
    asyncio.run(main())