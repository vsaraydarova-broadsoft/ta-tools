# -*- coding: utf-8 -*-
"""Error controller"""
import logging
from tg import request, expose, redirect
from srvreq.lib.base import BaseController

__all__ = ['TraceController']

log = logging.getLogger(__name__)

class TraceController(BaseController):

    @expose()
    def content(self, **kw):
        log.error( "******************** %s", kw)
        print "******************** %s", kw
        redirect('/settings',
                 output='8888888888\\n\n\n\n\n\nsdfasdfasdf')
