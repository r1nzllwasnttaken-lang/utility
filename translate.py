import os
import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

EMOJI_RUBY = "<:ruby:1539231061354086410>"
EMOJI_WRENCH = "<:wrench:1539230664996560967>"

DEEPL_API_KEY = os.getenv("DEEPL_API_KEY")

# Automatically switch endpoints based on API Key type (Free ends with :fx)
if DEEPL_API_KEY and DEEPL_API_KEY.endswith(":fx"):
    DEEPL_BASE_URL = "https://api-free.deepl.com/v2/translate"
else:
    DEEPL_BASE_URL = "https://api.deepl.com/v2/translate"

async def deepl_translate(text: str, target_lang: str) -> tuple[str, str]:
    headers = {
        "Authorization": f"DeepL-Auth-Key {DEEPL_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "text": [text],
        "target_lang": target_lang.upper()
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(DEEPL_BASE_URL, headers=headers, json=payload) as resp:
            if resp.status == 200:
                data = await resp.json()
                translation = data["translations"][0]
                return translation["text"], translation.get("detected_source_language", "AUTO")
            else:
                error_data = await resp.text()
                raise Exception(f"DeepL API Error ({resp.status}): {error_data}")

class TranslateCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="translate", description="Translate text using DeepL")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.describe(
        text="Text to translate",
        target_lang="Language code (e.g., EN, RO, DE, FR, ES, JA)",
        public="Set to True to make the response visible to everyone (Default: False)"
    )
    async def translate(
        self, 
        interaction: discord.Interaction, 
        text: str, 
        target_lang: str = "EN", 
        public: bool = False
    ):
        # Default ephemeral = True unless public parameter is set to True
        is_ephemeral = not public
        await interaction.response.defer(thinking=True, ephemeral=is_ephemeral)

        if not DEEPL_API_KEY:
            await interaction.followup.send(
                f"{EMOJI_WRENCH} DeepL API Key is missing in environment variables.", 
                ephemeral=is_ephemeral
            )
            return

        try:
            translated_text, detected_src = await deepl_translate(text, target_lang)

            embed = discord.Embed(
                description=f"## Ruby Translator{EMOJI_RUBY}",
                color=discord.Color.from_rgb(90, 160, 245)
            )
            
            # Format display text (truncate long text previews if needed)
            src_display = text if len(text) <= 1024 else text[:1021] + "..."
            embed.add_field(name=f"Original ({detected_src.upper()})", value=src_display, inline=False)
            embed.add_field(name=f"Translation ({target_lang.upper()})", value=translated_text, inline=False)
            
            embed.set_footer(text="Powered by DeepL")

            await interaction.edit_original_response(content=None, embed=embed)

        except Exception as e:
            await interaction.edit_original_response(
                content=f"{EMOJI_WRENCH} Translation error: `{str(e)}`"
            )

async def setup(bot):
    await bot.add_cog(TranslateCog(bot))
