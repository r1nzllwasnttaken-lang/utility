import discord
from discord import app_commands
from discord.ext import commands

EMOJI_RUBY = "<:ruby:1539231061354086410>"
EMOJI_WRENCH = "<:wrench:1539230664996560967>"

class ServerAvatarCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="savatar", description="Display a member's server-specific profile avatar")
    @app_commands.allowed_installs(guilds=True, users=False)
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @app_commands.describe(
        user="The server member whose server avatar you want to view (Default: Yourself)",
        public="Set to True to make the response visible to everyone (Default: False)"
    )
    async def savatar(
        self, 
        interaction: discord.Interaction, 
        user: discord.Member = None, 
        public: bool = False
    ):
        is_ephemeral = not public
        await interaction.response.defer(thinking=True, ephemeral=is_ephemeral)

        if not interaction.guild:
            await interaction.edit_original_response(
                content=f"{EMOJI_WRENCH} This command can only be used inside a server."
            )
            return

        target = user or interaction.user

        # Fetch guild-specific avatar, fallback to regular avatar if none set
        avatar_asset = target.guild_avatar or target.display_avatar
        avatar_url = avatar_asset.with_size(1024).url

        embed = discord.Embed(
            description=f"",
            color=discord.Color.from_rgb(240, 120, 180)
        )
        embed.add_field(name="Member", value=target.mention, inline=False)
        embed.set_image(url=avatar_url)
        embed.set_footer(text="Ruby Security")

        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Open Image", url=avatar_url, style=discord.ButtonStyle.link))

        await interaction.edit_original_response(content=None, embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(ServerAvatarCog(bot))
