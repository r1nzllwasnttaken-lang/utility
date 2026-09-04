import io
import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from PIL import Image

EMOJI_RUBY = "<:ruby:1539231061354086410>"
EMOJI_WRENCH = "<:wrench:1539230664996560967>"

ROBLOX_USERS_API = "https://users.roblox.com/v1/usernames/users"
ROBLOX_THUMBNAILS_API = "https://thumbnails.roblox.com/v1/users/avatar"
ROBLOX_HEADSHOT_API = "https://thumbnails.roblox.com/v1/users/avatar-headshot"
ROBLOX_BUST_API = "https://thumbnails.roblox.com/v1/users/avatar-bust"

async def get_roblox_user(username: str) -> tuple[int, str, str] | None:
    payload = {"usernames": [username], "excludeBannedUsers": False}
    async with aiohttp.ClientSession() as session:
        async with session.post(ROBLOX_USERS_API, json=payload) as resp:
            if resp.status == 200:
                data = await resp.json()
                results = data.get("data", [])
                if results:
                    user_data = results[0]
                    return user_data["id"], user_data["name"], user_data.get("displayName", user_data["name"])
    return None

async def fetch_avatar_urls(user_id: int) -> tuple[str, str, str]:
    params = {"userIds": [user_id], "size": "720x720", "format": "Png", "isCircular": "false"}
    
    async with aiohttp.ClientSession() as session:
        # Full Body
        async with session.get(ROBLOX_THUMBNAILS_API, params=params) as resp:
            body_data = await resp.json()
            body_url = body_data["data"][0]["imageUrl"]
            
        # Headshot
        async with session.get(ROBLOX_HEADSHOT_API, params=params) as resp:
            head_data = await resp.json()
            head_url = head_data["data"][0]["imageUrl"]

        # Bust
        async with session.get(ROBLOX_BUST_API, params=params) as resp:
            bust_data = await resp.json()
            bust_url = bust_data["data"][0]["imageUrl"]

    return body_url, head_url, bust_url

async def download_image(url: str, session: aiohttp.ClientSession) -> Image.Image:
    async with session.get(url) as resp:
        content = await resp.read()
        return Image.open(io.BytesIO(content)).convert("RGBA")

def create_composite_image(body_img: Image.Image, head_img: Image.Image, bust_img: Image.Image) -> io.BytesIO:
    # Canvas dimensions matching multi-render grid layout
    canvas_width = 1200
    canvas_height = 720
    canvas = Image.new("RGBA", (canvas_width, canvas_height), (0, 0, 0, 0))

    # Resize renders
    body_resized = body_img.resize((720, 720), Image.Resampling.LANCZOS)
    head_resized = head_img.resize((380, 380), Image.Resampling.LANCZOS)
    bust_resized = bust_img.resize((380, 380), Image.Resampling.LANCZOS)

    # Composite onto transparent background
    canvas.paste(body_resized, (0, 0), body_resized)
    canvas.paste(head_resized, (780, 0), head_resized)
    canvas.paste(bust_resized, (780, 340), bust_resized)

    # Save to buffer
    buffer = io.BytesIO()
    canvas.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer

class RAvatarCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ravatar", description="Display a Roblox user's avatar renders")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.describe(
        username="Roblox username to fetch",
        public="Set to True to make the response visible to everyone (Default: False)"
    )
    async def ravatar(
        self, 
        interaction: discord.Interaction, 
        username: str, 
        public: bool = False
    ):
        is_ephemeral = not public
        await interaction.response.defer(thinking=True, ephemeral=is_ephemeral)

        try:
            roblox_user = await get_roblox_user(username)
            if not roblox_user:
                await interaction.edit_original_response(
                    content=f"{EMOJI_WRENCH} Could not find Roblox user **{username}**."
                )
                return

            user_id, name, display_name = roblox_user
            body_url, head_url, bust_url = await fetch_avatar_urls(user_id)

            # Download renders and create composed PNG
            async with aiohttp.ClientSession() as session:
                body_img = await download_image(body_url, session)
                head_img = await download_image(head_url, session)
                bust_img = await download_image(bust_url, session)

            image_buffer = create_composite_image(body_img, head_img, bust_img)
            discord_file = discord.File(fp=image_buffer, filename="roblox_avatar.png")

            # Embed setup
            profile_url = f"https://www.roblox.com/users/{user_id}/profile"
            embed = discord.Embed(
                description=f"## [{display_name} (@{name})]({profile_url}) {EMOJI_RUBY}",
                color=discord.Color.from_rgb(0, 162, 255)
            )
            embed.set_image(url="attachment://roblox_avatar.png")
            embed.set_footer(text="Ruby Utilities")

            view = discord.ui.View()
            view.add_item(discord.ui.Button(label="Open Roblox Profile", url=profile_url, style=discord.ButtonStyle.link))

            await interaction.edit_original_response(
                content=None, 
                embed=embed, 
                attachments=[discord_file], 
                view=view
            )

        except Exception as e:
            await interaction.edit_original_response(
                content=f"{EMOJI_WRENCH} Error fetching Roblox avatar: `{str(e)}`"
            )

async def setup(bot):
    await bot.add_cog(RAvatarCog(bot))
