# -*- coding: utf-8 -*-
"""Sample controller with all its actions protected."""
import logging
from tg import expose
from srvreq.model import DBSession
from srvreq.model.request import Request


from srvreq.lib.base import BaseController

__all__ = ['XSPController']

log = logging.getLogger(__name__)

class XSPController(BaseController):
    """Sample controller-wide authorization"""

    @expose('srvreq.templates.requests')
    def index(self):
        requests = DBSession.query(Request)
        log.error("***** %s" % requests)
        return dict(page='xspreq', requests=requests, title="XSP Requests")

    @expose('srvreq.templates.index')
    def some_where(self):
        """Let the user know that this action is protected too."""
        return dict(page='some_where')
