import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

EMOJI_RUBY = "<:ruby:1539231061354086410>"
EMOJI_WRENCH = "<:wrench:1539230664996560967>"

URBAN_BASE_URL = "https://api.urbandictionary.com/v0/define"

# Helper function to remove brackets [word] that Urban Dictionary includes in text
def clean_ud_text(text: str) -> str:
    return text.replace("[", "").replace("]", "")

async def fetch_ud_definition(word: str) -> dict | None:
    async with aiohttp.ClientSession() as session:
        async with session.get(URBAN_BASE_URL, params={"term": word}) as resp:
            if resp.status == 200:
                data = await resp.json()
                results = data.get("list", [])
                return results[0] if results else None
            else:
                raise Exception(f"Urban Dictionary API error ({resp.status})")

class DefineCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="define", description="Look up a term on Urban Dictionary")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.describe(
        term="The word or phrase to look up",
        public="Set to True to make the response visible to everyone (Default: False)"
    )
    async def define(
        self, 
        interaction: discord.Interaction, 
        term: str, 
        public: bool = False
    ):
        is_ephemeral = not public
        await interaction.response.defer(thinking=True, ephemeral=is_ephemeral)

        try:
            entry = await fetch_ud_definition(term)

            if not entry:
                await interaction.edit_original_response(
                    content=f"{EMOJI_WRENCH} No definitions found for **{term}**."
                )
                return

            word = entry.get("word", term)
            definition = clean_ud_text(entry.get("definition", "No definition provided."))
            example = clean_ud_text(entry.get("example", ""))
            thumbs_up = entry.get("thumbs_up", 0)
            thumbs_down = entry.get("thumbs_down", 0)
            permalink = entry.get("permalink", f"https://www.urbandictionary.com/define.php?term={term}")

            if len(definition) > 1024:
                definition = definition[:1021] + "..."

            embed = discord.Embed(
                description=f"## Definition{EMOJI_RUBY}",
                color=discord.Color.from_rgb(230, 75, 60)
            )

            embed.add_field(name="Term", value=f"**{word}**", inline=False)
            embed.add_field(name="Definition", value=definition, inline=False)

            if example:
                if len(example) > 1024:
                    example = example[:1021] + "..."
                embed.add_field(name="Example", value=f"*{example}*", inline=False)

            embed.set_footer(text="Ruby Security")

            view = discord.ui.View()
            view.add_item(discord.ui.Button(label="Open on Urban Dictionary", url=permalink, style=discord.ButtonStyle.link))

            await interaction.edit_original_response(content=None, embed=embed, view=view)

        except Exception as e:
            await interaction.edit_original_response(
                content=f"{EMOJI_WRENCH} Dictionary error: `{str(e)}`"
            )

async def setup(bot):
    await bot.add_cog(DefineCog(bot))
