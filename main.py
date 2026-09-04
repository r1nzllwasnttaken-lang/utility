import os
import threading
import discord
from discord.ext import commands
from flask import Flask

# ---------------------------------------------------------
# Flask Web Server (For 24/7 Keep-Alive)
# ---------------------------------------------------------
app = Flask(__name__)

@app.route('/')
def home():
    return "Ruby Security Bot is running!"

@app.route('/health')
def health():
    return {"status": "ok", "bot_ready": bot.is_ready()}, 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# ---------------------------------------------------------
# Discord Bot Core Setup
# ---------------------------------------------------------
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

class RubyBot(commands.Bot):
    def __init__(self):
        # Configure Intents including privileged Message Content Intent
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # Load command cogs
        await self.load_extension("scan")
        await self.load_extension("translate")
        await self.load_extension("define")
        await self.load_extension("avatar")
        await self.load_extension("status")
        await self.load_extension("whois")
        
        # Sync slash commands globally
        await self.tree.sync()
        print("Ruby slash commands synced globally!")

bot = RubyBot()

if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    bot.run(DISCORD_TOKEN)
