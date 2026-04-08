
from sqlalchemy import create_engine,update, delete, select
import os

# Create engine
CONNECTION = os.getenv("POSTGRES_CONNECTION")
assert CONNECTION is not None
engine = create_engine(CONNECTION, echo=True)


# Import Schema
from .base import Base
from .tables import Character, Account

# Create the database (ensure database actually exists)
Base.metadata.create_all(engine)



