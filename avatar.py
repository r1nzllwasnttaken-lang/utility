import discord
from discord import app_commands
from discord.ext import commands

EMOJI_RUBY = "<:ruby:1539231061354086410>"

class AvatarCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="avatar", description="Display a user's profile avatar")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.describe(
        user="The user whose avatar you want to view (Default: Yourself)",
        public="Set to True to make the response visible to everyone (Default: False)"
    )
    async def avatar(
        self, 
        interaction: discord.Interaction, 
        user: discord.User = None, 
        public: bool = False
    ):
        is_ephemeral = not public
        await interaction.response.defer(thinking=True, ephemeral=is_ephemeral)

        target = user or interaction.user
        avatar_url = target.display_avatar.with_size(1024).url

        embed = discord.Embed(
            description=f"",
            color=discord.Color.from_rgb(150, 100, 240)
        )
        embed.add_field(name="User", value=target.mention, inline=False)
        embed.set_image(url=avatar_url)
        embed.set_footer(text="Ruby Security")

        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Open Image", url=avatar_url, style=discord.ButtonStyle.link))

        await interaction.edit_original_response(content=None, embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(AvatarCog(bot))
