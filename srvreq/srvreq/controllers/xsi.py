# -*- coding: utf-8 -*-
"""Sample controller with all its actions protected."""
import logging
import base64
from tg import expose, redirect, flash
from srvreq.lib.base import BaseController
import srvreq.model.request as requests

import server.tools as tools
import server.utils as utils

__all__ = ['XSIController']

log = logging.getLogger(__name__)

class XSIController(BaseController):
    """Sample controller-wide authorization"""

    REQUESTS = {}
    REQUEST_NAMES = []

    base_dict = {
        "title" : "XSP Requests",
        "page" : "xsirequest"
    }

    def __init__(self, settings_controller):
        BaseController.__init__(self)
        self.sc = settings_controller
        requests.add_xsi_requests(self.REQUESTS, self.REQUEST_NAMES)
        self.base_dict["requests"] = self.REQUESTS
        self.base_dict["request_names"] = self.REQUEST_NAMES

    def _before(self, *args, **kw):
        if not self.sc.get_user_prop("fetched"):
            flash('Please set xsp user settings', 'error')
            redirect("/settings")
        self.base_dict["user"] = self.sc.get_user()

    def _render_page(self, pagename, **kw):
        req = self.REQUESTS[pagename]
        for arg in req.arguments:
            arg.value = self.sc.get_user_prop(arg.name, arg.value)
        self.base_dict["curr_request"] = req
        self.base_dict["output"] = ''
        return self.base_dict

    def _execute_reqest(self, method, **kw):
        xsi = tools.create_xsi_tool_for_account(
            self.sc.get_server(),
            self.sc.get_user_data())
        try:
            func = getattr(xsi, method)
            args = []
            _kwargs = False
            for a in self.REQUESTS[method].arguments:
                if a.type == 'bool':
                    self.sc.set_user_prop(a.name, {"checked" : "on" if kw.get(a.name) else "off"})
                    kw[a.name] = bool(kw.get(a.name) and kw[a.name] in ['on'])
                else:
                    assert a.name in kw, "missing argument %s" % a.name
                    self.sc.set_user_prop(a.name, utils.xml_string(kw[a.name]))
                if a.encode:
                    kw[a.name] = base64.b64encode(kw[a.name])
                if a.optional and kw[a.name] == '':
                      kw[a.name] = a.value
                if a.pos > -1:
                    args.insert(a.pos, kw[a.name])
                else:
                    _kwargs = True
            log.info("Call %s with %s and %s" % (method, args, kw))
            res = func(*args, **kw) if _kwargs else func(*args)
        except AttributeError as ae:
            flash('Please set xsi user settings', 'error')
        except AssertionError as ae:
            flash('XSI call failed: %s' % ae, 'error')
            self.base_dict["output"] = "%s" % ae
            return self.base_dict
        self.base_dict["output"] = "%s" % utils.xml_string(res)
        return self.base_dict

    @expose('srvreq.templates.xsirequest')
    def _default(self, pagename="", **kw):
        if pagename in self.REQUESTS.keys():
            return self._render_page(pagename, **kw)
        elif pagename[0:5] == 'call_' and pagename[5:] in self.REQUESTS.keys():
            return self._execute_reqest(pagename[5:], **kw)
        else:
            flash('Unsupported method', 'error')
            redirect("/settings")

    @expose('srvreq.templates.xsirequest')
    def index(self):
        return self.base_dict
