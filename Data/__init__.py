from sqlalchemy import create_engine, update, delete, select
from sqlalchemy.exc import OperationalError
import os
import tenacity

CONNECTION = os.getenv("POSTGRES_CONNECTION")
assert CONNECTION is not None
engine = create_engine(CONNECTION, echo=True, pool_pre_ping=True)

from .base import Base
from .tables import Character, Account, Business

@tenacity.retry(
    wait=tenacity.wait_exponential(multiplier=1, max=60),
    retry=tenacity.retry_if_exception_type(OperationalError)
)
def initialize_database(): Base.metadata.create_all(engine)

