"""
Entry point script!
"""

from Core.bot import bot
import dotenv
import os
dotenv.load_dotenv()
token = os.getenv("TOKEN")
assert type(token) == str
bot.run(token)
