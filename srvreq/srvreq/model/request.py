from sqlalchemy import *
from sqlalchemy.orm import mapper, relation
from sqlalchemy import Table, ForeignKey, Column
from sqlalchemy.types import Integer, String

from srvreq.model import DeclarativeBase, metadata, DBSession


class Request(DeclarativeBase):
    __tablename__ = 'requests'

    id = Column(Integer, primary_key=True)
    name = Column(String(40), unique=True)
    display_name = Column(String(40))
    type = Column(String(10))