from discord.ext.commands import AutoShardedBot
import discord
import os

# Intents
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

# Bot
bot = AutoShardedBot(
    intents=intents,
    command_prefix="r!"
)

@bot.event
async def on_ready():
    print(f"Logged in as: {bot.user.name}") # type:ignore
    for ext in os.listdir("Ext"):
        if ext.endswith(".py"):
            print(f"Loading: {ext}")
            await bot.load_extension("Ext." + ext[:-3])
    await bot.tree.sync()
    print("Commands Synced")

