from sqlmodel import ForeignKey
from .base import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, JSON
from enum import Enum

class ItemType(Enum):
    GUN = "gun"
    OTHER = "other"

class Item(Base):
    __tablename__ = "items" #type:ignore

    name: Mapped[str] = mapped_column(String, primary_key=True)
    type: Mapped[ItemType] = mapped_column()
    character_name: Mapped[str] = mapped_column(ForeignKey("characters.name"))
    
    character: Mapped["Character"] = relationship(back_populates="items")


class Character(Base):
    __tablename__ = "characters" #type:ignore 
    
    name: Mapped[str] = mapped_column(String, primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    
    items: Mapped[list["Item"]] = relationship(back_populates="items")
    account: Mapped["Account"] = relationship()

class Account(Base):
    __tablename__ = "accounts" #type:ignore

    id: Mapped[int] = mapped_column(primary_key=True)
    balance: Mapped[int] = mapped_column(default=0)
    

