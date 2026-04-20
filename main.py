"""
Entry point script!
"""

from Core.bot import bot
import dotenv
import os
import sys
sys.dont_write_bytecode = True
dotenv.load_dotenv()
token = os.getenv("TOKEN")
assert type(token) == str
bot.run(token)
