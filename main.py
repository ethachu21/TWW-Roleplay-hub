"""
Entry point script!
"""

from Core.bot import bot
import dotenv
import os

token = os.getenv("TOKEN")
assert type(token) == str
bot.run(token)
