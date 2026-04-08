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
    print(f"Logged in as: {bot.user.name}",flush=True) # type:ignore
    for ext in os.listdir("Ext"):
        if ext.endswith(".py"):
            print(f"Loading: {ext}", flush=True)
            await bot.load_extension("Ext." + ext[:-3])
    await bot.tree.sync()
    print("Commands Synced",flush=True)
    await bot.change_presence(activity=discord.CustomActivity("I wrote this god forsaken string at 01:05 AM --ethachu21")) 

@bot.tree.command(name="ping", description="Check the bot's latency")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"Pong! {round(bot.latency * 1000)}ms")

@bot.event
async def on_message(msg: discord.Message):
    if msg.content == "who am i" and msg.author.name == "can_van_der_linde":
        await msg.reply("you are dutch, an absolute madlad")
    elif msg.content == "who am i":
        await msg.reply(f"You are {msg.author.mention}")
