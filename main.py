"""
Entry point script!
"""

from Core.bot import bot
from Data import initialize_database
import dotenv
import os
import sys

sys.dont_write_bytecode = True
dotenv.load_dotenv()

# load the db before the bot or else... heartbeat issues
initialize_database()

token = os.getenv("TOKEN")
assert type(token) == str
bot.run(token)
