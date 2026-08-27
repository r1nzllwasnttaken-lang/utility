import os
import asyncio
import threading
import hashlib
import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "Ruby is onlie"

@app.route('/health')
def health():
    return {"status": "ok", "bot_ready": bot.is_ready()}, 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

TRIAGE_API_URL = "https://triage.ac/api/v1"
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
TRIAGE_API_KEY = os.getenv("TRIAGE_API_KEY")

class RubyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print("Slash Commands Synced")

bot = RubyBot()

async def submit_and_poll_triage(file_bytes: bytes, filename: str, interaction: discord.Interaction):
    headers = {"Authorization": f"Bearer {TRIAGE_API_KEY}"}
    
    async with aiohttp.ClientSession() as session:
        data = aiohttp.FormData()
        data.add_field('file', file_bytes, filename=filename)
        
        async with session.post(f"{TRIAGE_API_URL}/samples", headers=headers, data=data) as resp:
            if resp.status != 200:
                raise Exception(f"API returned status {resp.status}")
            sample_data = await resp.json()
            sample_id = sample_data.get("id")

        for elapsed in range(10, 180, 10):
            await asyncio.sleep(10)
            await interaction.edit_original_response(
                content=f"**Checking...** ({elapsed}s elapsed)\n*Analyzing...*"
            )

            async with session.get(f"{TRIAGE_API_URL}/samples/{sample_id}/overview", headers=headers) as rep_resp:
                if rep_resp.status == 200:
                    report = await rep_resp.json()
                    return report, sample_id
                elif rep_resp.status == 404:
                    continue
                else:
                    raise Exception("Unexpected error while fetching report status.")

        raise TimeoutError("Sandbox detonator timed out after 3 minutes.")

@bot.tree.command(name="scan", description="Deep-scan a file for threats using Hatching Triage Sandbox")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.describe(file="Select the file attachment to analyze")
async def scan_file(interaction: discord.Interaction, file: discord.Attachment):
    await interaction.response.defer(thinking=True, ephemeral=True)

    if file.size > 25 * 1024 * 1024:
        await interaction.followup.send("**File Size Exceeded:** Maximum size for analysis is 25 MB.", ephemeral=True)
        return

    file_bytes = await file.read()
    sha256_hash = hashlib.sha256(file_bytes).hexdigest()

    try:
        await interaction.edit_original_response(content="📤 **Uploading payload to Hatching Triage Sandbox...**")
        report, sample_id = await submit_and_poll_triage(file_bytes, file.filename, interaction)

        score = report.get("analysis", {}).get("score", 0)
        family = report.get("targets", [{}])[0].get("family", "Generic / Unclassified")
        
        if score >= 8:
            color = discord.Color.from_rgb(255, 45, 85)
            verdict_badge = "CRITICAL MALWARE DETECTED"
            risk_desc = f"High severity activity registered. Identified signature: `{family}`."
        elif score >= 5:
            color = discord.Color.from_rgb(255, 149, 0)
            verdict_badge = "SUSPICIOUS BEHAVIOR"
            risk_desc = "Suspicious system interactions or API calls recorded during execution."
        elif score >= 1:
            color = discord.Color.from_rgb(255, 204, 0)
            verdict_badge = "LOW RISK / UNKNOWN"
            risk_desc = "Minor low-risk anomalies spotted. Likely benign executable."
        else:
            color = discord.Color.from_rgb(48, 209, 88)
            verdict_badge = "CLEAN / NO THREATS FOUND"
            risk_desc = "No malicious indicators or suspicious network calls detected."

        embed = discord.Embed(
            title=f"Security Report • {file.filename}",
            description=f"**Verdict:** `{verdict_badge}`\n{risk_desc}",
            color=color
        )
        
        filled_blocks = int(score)
        score_bar = "🟥" * filled_blocks + "⬛" * (10 - filled_blocks) if score >= 5 else "🟩" * filled_blocks + "⬛" * (10 - filled_blocks)
        
        embed.add_field(name="Threat Score", value=f"{score_bar} **{score}/10**", inline=False)
        embed.add_field(name="File Name", value=f"`{file.filename}`", inline=True)
        embed.add_field(name="File Size", value=f"`{round(file.size / 1024, 2)} KB`", inline=True)
        embed.add_field(name="SHA-256 Digest", value=f"```text\n{sha256_hash}\n```", inline=False)
        embed.set_footer(text="Ruby Security Engine • Hatching Triage Sandbox", icon_url=bot.user.display_avatar.url)

        view = discord.ui.View()
        report_url = f"https://triage.ac/{sample_id}"
        view.add_item(discord.ui.Button(label="View Full Sandbox Interactive Analysis", url=report_url, style=discord.ButtonStyle.link, emoji="🔗"))

        await interaction.edit_original_response(content=None, embed=embed, view=view)

    except TimeoutError as te:
        await interaction.edit_original_response(content=f"**Analysis Timed Out:** {str(te)}")
    except Exception as e:
        await interaction.edit_original_response(content=f"**Scan Error:** `{str(e)}`")

def start_bot():
    bot.run(DISCORD_TOKEN)

if __name__ == "__main__":
    # Start Flask server in a daemon thread so it runs concurrently with Discord.py
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Run Discord Bot on the main thread
    start_bot()
