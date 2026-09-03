import os
import logging
import requests
import google.generativeai as genai
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ==================== CONFIGURATION ====================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")  # e.g. "@marketsingal09"
ADMIN_USER_ID = os.getenv("ADMIN_USER_ID")  # Numeric ID from @userinfobot
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Configure Google Gemini SDK
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# Posting interval in minutes (default: 240 mins / 4 hours)
POST_INTERVAL_MINUTES = int(os.getenv("POST_INTERVAL_MINUTES", "240"))

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# ==================== DATA FETCHERS ====================
def get_crypto_prices() -> str:
    """Fetch real-time crypto prices from CoinGecko API"""
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,solana,cardano,binancecoin&vs_currencies=usd&include_24hr_change=true"
        response = requests.get(url, timeout=10).json()

        btc = response.get("bitcoin", {})
        eth = response.get("ethereum", {})
        sol = response.get("solana", {})
        ada = response.get("cardano", {})
        bnb = response.get("binancecoin", {})

        msg = (
            "📊 *MarketSignalBot — Live Crypto Update*\n\n"
            f"₿ *Bitcoin (BTC):* ${btc.get('usd', 0):,.2f} ({btc.get('usd_24h_change', 0):+.2f}%)\n"
            f"💎 *Ethereum (ETH):* ${eth.get('usd', 0):,.2f} ({eth.get('usd_24h_change', 0):+.2f}%)\n"
            f"⚡ *Solana (SOL):* ${sol.get('usd', 0):,.2f} ({sol.get('usd_24h_change', 0):+.2f}%)\n"
            f"🟡 *Binance Coin (BNB):* ${bnb.get('usd', 0):,.2f} ({bnb.get('usd_24h_change', 0):+.2f}%)\n"
            f"🔵 *Cardano (ADA):* ${ada.get('usd', 0):,.2f} ({ada.get('usd_24h_change', 0):+.2f}%)\n\n"
            "⚡ *Forex | ₿ Crypto | 📈 Market Signals | 📰 News | 🔔 Alerts*\n\n"
            "⚠️ *Educational information only. Not financial advice.*"
        )
        return msg
    except Exception as e:
        logging.error(f"Error fetching market prices: {e}")
        return "⚠️ Couldn't fetch market updates right now."

def ask_ai(question: str) -> str:
    """Answer questions using Google Gemini Free API"""
    if not GEMINI_API_KEY:
        return "🧠 AI assistant is currently disabled. Set your GEMINI_API_KEY environment variable."
    
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = (
            "You are MarketSignalBot, an expert assistant for Forex and Crypto trading. "
            "Provide concise, accurate answers in Markdown format. "
            "Never guarantee financial returns or provide direct investment advice.\n\n"
            f"User question: {question}"
        )
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        logging.error(f"Gemini API Error: {e}")
        return "⚠️ Sorry, I could not process your AI request right now."

# ==================== CHANNEL POSTING JOB ====================
async def auto_post_job(context: ContextTypes.DEFAULT_TYPE):
    """Sends a live price update directly to your channel"""
    if not CHANNEL_ID:
        logging.warning("CHANNEL_ID is not configured. Auto-post skipped.")
        return

    message = get_crypto_prices()
    try:
        await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text=message,
            parse_mode="Markdown"
        )
        logging.info(f"Successfully posted update to {CHANNEL_ID}")
    except Exception as e:
        logging.error(f"Failed to post to channel ({CHANNEL_ID}): {e}")

# ==================== HANDLERS ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📊 Live Prices", callback_data="prices")],
        [InlineKeyboardButton("ℹ️ Help & Commands", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = (
        "📊 *MarketSignalBot* — Your smart companion for Forex & Crypto markets.\n\n"
        "Get live updates, price alerts, analysis, and news in one place.\n\n"
        "⚡ Forex | ₿ Crypto | 📈 Market Signals | 📰 News | 🔔 Alerts\n\n"
        "💡 *Tip:* Send any market question to chat with AI!"
    )
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📖 *MarketSignalBot Commands*\n\n"
        "• /start — Launch main menu\n"
        "• /help — Show help message\n"
        "• /market — Fetch real-time market prices\n"
        "• /post — Instantly publish an update to the channel\n\n"
        "💬 *AI Chat:* Send any text message to receive an AI response."
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def market_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = get_crypto_prices()
    await update.message.reply_text(message, parse_mode="Markdown")

async def force_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manual trigger to immediately push updates to channel"""
    user_id = str(update.effective_user.id)
    if ADMIN_USER_ID and user_id != str(ADMIN_USER_ID):
        await update.message.reply_text("⛔ Admin access required.")
        return

    await auto_post_job(context)
    await update.message.reply_text("✅ Market update pushed to channel immediately.")

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "prices":
        message = get_crypto_prices()
        await query.message.reply_text(message, parse_mode="Markdown")
    elif query.data == "help":
        await help_command(update, context)

async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    ai_response = ask_ai(user_text)
    await update.message.reply_text(ai_response, parse_mode="Markdown")

# ==================== APPLICATION BOOTSTRAP ====================
async def post_init(application):
    """Executes auto-post immediately upon container startup"""
    interval_seconds = POST_INTERVAL_MINUTES * 60
    application.job_queue.run_repeating(
        callback=auto_post_job,
        interval=interval_seconds,
        first=1,
        name="auto_post_job"
    )
    logging.info(f"Auto-post job armed: Initial post in 1 second, repeating every {POST_INTERVAL_MINUTES} mins.")

def main():
    if not BOT_TOKEN:
        raise ValueError("CRITICAL ERROR: BOT_TOKEN is missing! Set it in Railway Variables.")

    app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("market", market_command))
    app.add_handler(CommandHandler("post", force_post))
    app.add_handler(CallbackQueryHandler(button_click))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_message))

    logging.info("MarketSignalBot starting polling...")
    app.run_polling()

if __name__ == "__main__":
    main()
