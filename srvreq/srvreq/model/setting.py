from sqlalchemy import *
from sqlalchemy.orm import mapper, relation
from sqlalchemy import Table, ForeignKey, Column
from sqlalchemy.types import Integer, String

from srvreq.model import DeclarativeBase, metadata, DBSession

class Setting(DeclarativeBase):
    __tablename__ = 'settings'

    id = Column(Integer, primary_key=True)
    name = Column(String(40), unique=True)
    value = Column(String(50))