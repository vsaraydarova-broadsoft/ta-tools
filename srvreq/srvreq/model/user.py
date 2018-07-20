from sqlalchemy import *
from sqlalchemy.orm import mapper, relation
from sqlalchemy import Table, ForeignKey, Column
from sqlalchemy.types import Integer, String, Boolean

from srvreq.model import DeclarativeBase, metadata, DBSession

ACCOUNTS = {}

class XSPUser(DeclarativeBase):
    __tablename__ = 'xsp_users'

    id = Column(Integer, primary_key=True)
    xsp_password = Column(String(50), nullable=False)
    active = Column(Boolean, default=False)