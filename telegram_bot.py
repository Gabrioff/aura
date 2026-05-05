import os
import aiohttp
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiohttp import web

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")
AI_API_URL = os.getenv("AI_API_URL", "https://pepeoff-aura.hf.space/ask_ai")

# La base de la URL para hacer las consultas a los nuevos endpoints
API_BASE_URL = AI_API_URL.replace("/ask_ai", "")

if not TELEGRAM_BOT_TOKEN: raise ValueError("❌ ERROR CRÍTICO: No se encontró TELEGRAM_TOKEN.")

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

def format_currency(value):
    if value >= 1_000_000_000: return f"${value/1_000_000_000:.2f}B"
    elif value >= 1_000_000: return f"${value/1_000_000:.2f}M"
    elif value == 0: return "N/A"
    return f"${value:,.2f}"

async def fetch_api_data(endpoint: str, method: str = "GET", payload: dict = None) -> dict:
    headers = {"Authorization": f"Bearer {HF_TOKEN}", "Content-Type": "application/json"}
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
    await fetch_api_data(f"/balance/{message.from_user.id}")
    await message.answer(
        "🤖 *Dark Analyst V2*\n"
        "Comandos disponibles:\n"
        "🔹 `/p <moneda>` - Analizar. Ejemplo: `/p sol` o `/p btc`\n"
        "🔹 `/balance` - Ver tus fondos demo disponibles.",
        parse_mode=ParseMode.MARKDOWN
    )

@dp.message(Command("balance"))
async def check_balance(message: types.Message):
    user_id = message.from_user.id
    response = await fetch_api_data(f"/balance/{user_id}")
    balance = response["data"].get("balance", 0.00) if response["status"] == 200 else 0.00

    await message.answer(f"💼 **CUENTA DEMO**\n\n💰 *Balance:* `${balance:.2f} USD`", parse_mode=ParseMode.MARKDOWN)

@dp.message(Command("p"))
async def analyze_crypto(message: types.Message):
    args = message.text.split()
    symbol = "SOL" if len(args) == 1 else args[1].upper()

    status_msg = await message.answer(f"🔄 Consultando al Cerebro (Hugging Face) para {symbol}...", parse_mode=ParseMode.MARKDOWN)

    # 1. Le pasamos toda la responsabilidad a Hugging Face
    resp = await fetch_api_data("/analyze", method="POST", payload={"symbol": symbol})
    
    if resp["status"] == 200:
        data = resp["data"]
        api_data = data["api_data"]
        math_data = data["math_data"]
        ai_response = data["ai_response"]

        final_report = (
            f"📊 **REPORTE: {api_data['name']} ({api_data['symbol']})** - Rank `#{api_data['rank']}`\n\n"
            f"💰 *Precio:* `${api_data['price']}` ({api_data['change_24h']:.2f}%)\n"
            f"🏦 *Market Cap:* `{format_currency(api_data['market_cap'])}`\n"
            f"🌊 *Volumen (24h):* `{format_currency(api_data['volume_24h'])}`\n"
            f"🎯 *Pivote:* `{math_data['punto_pivote']}`\n"
            f"🛡️ *Sup:* `{math_data['soporte_1']}` | ⚔️ *Res:* `{math_data['resistencia_1']}`\n\n"
            f"🧠 **ANÁLISIS INSTITUCIONAL:**\n{ai_response}"
        )
        if len(final_report) > 4000: final_report = final_report[:4000] + "..."
        await status_msg.edit_text(final_report, parse_mode=ParseMode.MARKDOWN)

    elif resp["status"] == 404:
        await status_msg.edit_text(f"❌ Error: La IA no encontró la moneda '{symbol}' en el mercado.")
    elif resp["status"] == 429:
        await status_msg.edit_text("⏳ La IA está ocupada procesando otras peticiones. Intenta de nuevo en unos segundos.")
    else:
        await status_msg.edit_text(f"❌ Error del Cerebro (HTTP {resp['status']}): {resp['data']}")

# --- SERVIDOR WEB DUMMY PARA EVITAR EL ERROR DE RENDER ---
async def handle_ping(request): return web.Response(text="Bot de Telegram activo y funcionando.")

async def init_web_server():
    app = web.Application()
    app.router.add_get('/', handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"✅ Servidor web de respaldo iniciado en el puerto {port}")

async def main():
    await init_web_server()
    print("Iniciando polling de Telegram...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())