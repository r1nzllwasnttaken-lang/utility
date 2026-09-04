import os
import time
import discord
import psutil
from discord import app_commands
from discord.ext import commands

EMOJI_RUBY = "<:ruby:1539231061354086410>"

class StatusCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = time.time()

    @app_commands.command(name="status", description="Display bot system status and latency")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.describe(
        public="Set to True to make the response visible to everyone (Default: False)"
    )
    async def status(self, interaction: discord.Interaction, public: bool = False):
        is_ephemeral = not public
        await interaction.response.defer(thinking=True, ephemeral=is_ephemeral)

        # Uptime Calculation
        uptime_seconds = int(time.time() - self.start_time)
        days, remainder = divmod(uptime_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{days}d {hours}h {minutes}m {seconds}s"

        # System Metrics
        process = psutil.Process(os.getpid())
        ram_usage = process.memory_info().rss / 1024 / 1024  # Convert to MB
        cpu_usage = psutil.cpu_percent()
        ping = round(self.bot.latency * 1000)

        embed = discord.Embed(
            description=f"## Ruby System Status {EMOJI_RUBY}",
            color=discord.Color.from_rgb(150, 100, 240)
        )
        embed.add_field(name="Latency", value=f"`{ping} ms`", inline=True)
        embed.add_field(name="RAM Usage", value=f"`{ram_usage:.2f} MB`", inline=True)
        embed.add_field(name="CPU Usage", value=f"`{cpu_usage}%`", inline=True)
        embed.add_field(name="Uptime", value=f"`{uptime_str}`", inline=True)
        embed.add_field(name="Guilds", value=f"`{len(self.bot.guilds)}`", inline=True)
        embed.add_field(name="API State", value="`Online & Operational`", inline=True)
        embed.set_footer(text="Ruby Utilities")

        await interaction.edit_original_response(embed=embed)

async def setup(bot):
    await bot.add_cog(StatusCog(bot))
