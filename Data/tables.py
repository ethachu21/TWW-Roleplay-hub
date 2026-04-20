from sqlalchemy import ForeignKey, BigInteger
from .base import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, JSON
from enum import Enum



class Character(Base):
    __tablename__ = "characters"
    
    name: Mapped[str] = mapped_column(String, primary_key=True)
    discord_id: Mapped[int] = mapped_column(BigInteger)
    business_name: Mapped['str'] = mapped_column(ForeignKey("businesses.name"), nullable=True)

    account: Mapped["Account"] = relationship(back_populates="character_holder")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.account:
            self.account = Account(type="CHAR", balance=400)

class Business(Base):
    __tablename__ = "businesses"
    
    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True)
    owner: Mapped["Character"] = relationship()

    
    account: Mapped["Account"] = relationship(back_populates="business_holder")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.account:
            self.account = Account(type="BIZ", balance=2000)

class Account(Base):
    __tablename__ = "accounts" 

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    type: Mapped[str] = mapped_column(String)
    balance: Mapped[int] = mapped_column(default=0)
    
    character_name: Mapped[str | None] = mapped_column(ForeignKey("characters.name"))
    character_holder: Mapped["Character"] = relationship(back_populates="account")

    business_id: Mapped[str | None] = mapped_column(ForeignKey("businesses.id"))
    business_holder: Mapped["Business"] = relationship(back_populates="account")

    @property
    def holder(self) -> "Character | Business | None":
        return self.character_holder or self.business_holder



