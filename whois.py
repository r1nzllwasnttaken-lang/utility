import discord
from discord import app_commands
from discord.ext import commands

EMOJI_RUBY = "<:ruby:1539231061354086410>"

class WhoIsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="whois", description="Display general information about a Discord user")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.describe(
        user="The user to lookup (Default: Yourself)",
        public="Set to True to make the response visible to everyone (Default: False)"
    )
    async def whois(
        self, 
        interaction: discord.Interaction, 
        user: discord.User = None, 
        public: bool = False
    ):
        is_ephemeral = not public
        await interaction.response.defer(thinking=True, ephemeral=is_ephemeral)

        target = user or interaction.user
        
        # Fetch full user to resolve banner and accent colors if available
        try:
            target = await self.bot.fetch_user(target.id)
        except Exception:
            pass

        created_timestamp = int(target.created_at.timestamp())
        avatar_url = target.display_avatar.with_size(1024).url

        embed = discord.Embed(
            description=f"## User Profile Info {EMOJI_RUBY}",
            color=target.accent_color or discord.Color.from_rgb(150, 100, 240)
        )
        embed.set_thumbnail(url=avatar_url)
        embed.add_field(name="Username", value=f"`@{target.name}`", inline=True)
        embed.add_field(name="Display Name", value=f"`{target.display_name}`", inline=True)
        embed.add_field(name="User ID", value=f"`{target.id}`", inline=True)
        embed.add_field(name="Account Created", value=f"<t:{created_timestamp}:F> (<t:{created_timestamp}:R>)", inline=False)
        embed.add_field(name="Bot Account", value=f"`{'Yes' if target.bot else 'No'}`", inline=True)
        embed.set_footer(text="Ruby Utilities")

        if target.banner:
            embed.set_image(url=target.banner.with_size(1024).url)

        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Open Avatar", url=avatar_url, style=discord.ButtonStyle.link))

        await interaction.edit_original_response(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(WhoIsCog(bot))
