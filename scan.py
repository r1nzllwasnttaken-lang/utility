import os
import asyncio
import hashlib
import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

EMOJI_RUBY = "<:ruby:1539231061354086410>"
EMOJI_WRENCH = "<:wrench:1539230664996560967>"

VT_API_KEY = os.getenv("VT_API_KEY")
VT_BASE_URL = "https://www.virustotal.com/api/v3"

async def poll_vt_analysis(analysis_id: str, session: aiohttp.ClientSession) -> dict:
    headers = {"x-apikey": VT_API_KEY}
    for _ in range(20):
        await asyncio.sleep(10)
        async with session.get(f"{VT_BASE_URL}/analyses/{analysis_id}", headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                if data.get("data", {}).get("attributes", {}).get("status") == "completed":
                    return data.get("data", {}).get("attributes", {}).get("stats", {})
            else:
                raise Exception(f"VirusTotal error ({resp.status})")
    raise TimeoutError("Scan took too long.")

async def scan_file_vt(file_bytes: bytes, filename: str) -> tuple[dict, str]:
    headers = {"x-apikey": VT_API_KEY}
    sha256 = hashlib.sha256(file_bytes).hexdigest()
    
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{VT_BASE_URL}/files/{sha256}", headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("data", {}).get("attributes", {}).get("last_analysis_stats", {}), sha256

        form = aiohttp.FormData()
        form.add_field('file', file_bytes, filename=filename)
        async with session.post(f"{VT_BASE_URL}/files", headers=headers, data=form) as resp:
            if resp.status != 200:
                raise Exception("Could not upload file to VirusTotal.")
            upload_data = await resp.json()
            analysis_id = upload_data.get("data", {}).get("id")

        stats = await poll_vt_analysis(analysis_id, session)
        return stats, sha256

async def scan_url_vt(url: str) -> tuple[dict, str]:
    headers = {"x-apikey": VT_API_KEY}
    url_id = hashlib.sha256(url.encode()).hexdigest()

    async with aiohttp.ClientSession() as session:
        async with session.get(f"{VT_BASE_URL}/urls/{url_id}", headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("data", {}).get("attributes", {}).get("last_analysis_stats", {}), url_id

        async with session.post(f"{VT_BASE_URL}/urls", headers=headers, data={"url": url}) as resp:
            if resp.status != 200:
                raise Exception("Could not submit link to VirusTotal.")
            upload_data = await resp.json()
            analysis_id = upload_data.get("data", {}).get("id")

        stats = await poll_vt_analysis(analysis_id, session)
        return stats, url_id

class ScanCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="scan", description="Scan a file or link for viruses using VirusTotal")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.describe(file="File attachment to scan", url="Website link to scan")
    async def scan(self, interaction: discord.Interaction, file: discord.Attachment = None, url: str = None):
        await interaction.response.defer(thinking=True, ephemeral=True)

        if not file and not url:
            await interaction.followup.send(f"{EMOJI_WRENCH} Provide either a file or a link to scan.", ephemeral=True)
            return

        try:
            if file:
                if file.size > 32 * 1024 * 1024:
                    await interaction.followup.send("File is too large (32MB limit).", ephemeral=True)
                    return

                file_bytes = await file.read()
                stats, item_id = await scan_file_vt(file_bytes, file.filename)
                item_name = file.filename
                vt_link = f"https://www.virustotal.com/gui/file/{item_id}"
                target_field_name = "Target File"

            else:
                stats, item_id = await scan_url_vt(url)
                item_name = url
                vt_link = f"https://www.virustotal.com/gui/url/{item_id}"
                target_field_name = "Target URL"

            malicious = stats.get("malicious", 0)
            suspicious = stats.get("suspicious", 0)
            harmless = stats.get("harmless", 0) + stats.get("undetected", 0)
            total = malicious + suspicious + harmless

            if malicious >= 5:
                color = discord.Color.from_rgb(235, 50, 50)
                verdict_text = "High Risk"
            elif malicious >= 1 or suspicious >= 2:
                color = discord.Color.from_rgb(240, 140, 30)
                verdict_text = "Suspicious"
            elif suspicious == 1:
                color = discord.Color.from_rgb(240, 200, 40)
                verdict_text = "Low Risk"
            else:
                color = discord.Color.from_rgb(40, 200, 100)
                verdict_text = "Clean / Safe"

            embed = discord.Embed(
                description=f"## Ruby Virus Scan {EMOJI_RUBY}",
                color=color
            )
            embed.add_field(name=target_field_name, value=f"`{item_name}`", inline=False)
            embed.add_field(name="Verdict", value=verdict_text, inline=True)
            embed.add_field(name="Detections", value=f"{malicious + suspicious} / {total} engines", inline=True)
            embed.set_footer(text="Ruby Security")

            view = discord.ui.View()
            view.add_item(discord.ui.Button(label="Open VirusTotal Report", url=vt_link, style=discord.ButtonStyle.link))

            await interaction.edit_original_response(content=None, embed=embed, view=view)

        except TimeoutError:
            await interaction.edit_original_response(content=f"{EMOJI_WRENCH} The scan took too long. Try again or check VirusTotal directly.")
        except Exception as e:
            await interaction.edit_original_response(content=f"{EMOJI_WRENCH} Scan error: `{str(e)}`")

async def setup(bot):
    await bot.add_cog(ScanCog(bot))
