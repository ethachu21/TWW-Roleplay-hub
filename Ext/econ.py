import discord
from discord.ext import commands
from discord import app_commands

class Cog(commands.Cog):
    def __init__(self, bot: commands.AutoShardedBot) -> None:
        super().__init__()
        self.bot = bot

async def setup(bot: commands.AutoShardedBot):
    await bot.add_cog(Cog(bot))
