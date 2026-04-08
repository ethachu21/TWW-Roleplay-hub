from sqlalchemy import ForeignKey, BigInteger
from .base import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, JSON
from enum import Enum



class Character(Base):
    __tablename__ = "characters"
    
    name: Mapped[str] = mapped_column(String, primary_key=True)
    discord_id: Mapped[int] = mapped_column(BigInteger) # Owner of the character
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    
    account: Mapped["Account"] = relationship()

class Account(Base):
    __tablename__ = "accounts" 

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    type: Mapped[str] = mapped_column(String, default="ACC") # e.g., ACC, BUS
    balance: Mapped[int] = mapped_column(default=0)
   





