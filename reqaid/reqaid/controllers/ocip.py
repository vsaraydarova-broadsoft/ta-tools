# -*- coding: utf-8 -*-
"""Sample controller with all its actions protected."""
import logging
import base64
from tg.i18n import lazy_ugettext as l_
from tg import predicates
from tg import expose, redirect, flash, require, request
from reqaid.lib.base import BaseController
import reqaid.model.request as requests

import server.tools as tools
import server.utils as utils

__all__ = ['OCIPController']

log = logging.getLogger(__name__)

class OCIPController(BaseController):
    """Sample controller-wide authorization"""
    allow_only = predicates.has_permission('manage', msg=l_('Please login with your XSI credentials'))

    REQUESTS = {}
    REQUEST_NAMES = []

    base_dict = {
        "title" : "OCIP Requests",
        "page" : "ociprequest"
    }

    def __init__(self, data_storage):
        BaseController.__init__(self)
        self.ds = data_storage
        requests.add_ocip_requests(self.REQUESTS, self.REQUEST_NAMES)
        self.base_dict["requests"] = self.REQUESTS
        self.base_dict["request_names"] = self.REQUEST_NAMES

    def _before(self, *args, **kw):
        self.base_dict["clear"] = self._has_settings("admin_username", "admin_password", "deviceType")
        print "***** clear ", self.base_dict["clear"]
        self.base_dict["user"] = request.identity['repoze.who.userid']

    def _render_page(self, pagename, **kw):
        log.debug("[OCIP] render page %s (%s)" % (pagename, kw))
        req = self.REQUESTS[pagename]
        for arg in req.arguments:
            arg.value = self.ds.get_user_prop(arg.name, arg.value)
        self.base_dict["curr_request"] = req
        self.base_dict["output"] = ''
        return self.base_dict

    def _execute_reqest(self, method, **kw):
        log.debug("[OCIP] execute %s(%s)" % (method, kw))
        oci = tools.create_oci_tool(username=self.ds.get_admin_username(),
                                    password=self.ds.get_admin_password(),
                                    server=self.ds.get_server())
        try:
            func = getattr(oci, method)
            args = []
            _kwargs = False
            for a in self.REQUESTS[method].arguments:
                if a.type == 'bool':
                    self.ds.set_user_prop(a.name, {"checked" : "on" if kw.get(a.name) else "off"})
                    kw[a.name] = bool(kw.get(a.name) and kw[a.name] in ['on'])
                else:
                    assert a.name in kw, "missing argument %s" % a.name
                    self.ds.set_user_prop(a.name, utils.xml_string(kw[a.name]))
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
            flash('OCI call failed: %s' % ae, 'error')
            self.base_dict["output"] = "%s" % ae
            return self.base_dict
        self.base_dict["output"] = "OCI Command: \n%s\n" \
                                   "OCI Response:\n%s\n" % (oci.oci_command, utils.xml_string(res))
        return self.base_dict

    @expose('reqaid.templates.ociprequest')
    def _default(self, pagename="", **kw):
        log.debug("[OCIP] open page %s (%s)" % (pagename, kw))
        if not (self.ds.get_user_prop("admin_username") and \
                self.ds.get_user_prop("admin_password")):
            redirect("ocipsettings", action="set_admin")
        elif not self.ds.get_user_prop("deviceType"):
            redirect("ocipsettings", action="set_device_type")
        if pagename in self.REQUESTS.keys():
            return self._render_page(pagename, **kw)
        elif pagename[0:5] == 'call_' and pagename[5:] in self.REQUESTS.keys():
            return self._execute_reqest(pagename[5:], **kw)
        else:
            log.error("[OCIP] Unsupported method %s", pagename)
            flash('Unsupported method', 'error')
            redirect("/ocip")

    @expose()
    def set_admin(self, **kw):
        log.debug("[OCIP] set_admin %s" % kw)
        self.ds.set_user_prop("admin_username", kw.get("admin_username"))
        self.ds.set_user_prop("admin_password", kw.get("admin_password"))
        redirect("ocipsettings", action="set_device_type")

    @expose()
    def clear_settings(self, **kw):
        log.debug("[OCIP] clear_settings %s" % kw)
        self.ds.delete_user_props(
            "admin_username", "admin_password",
            "deviceType", "type", "deviceName", "fileContent")
        redirect("/ocip")

    @expose()
    def set_device_type(self, **kw):
        log.debug("[OCIP] set_device_type %s" % kw)
        self.ds.set_user_prop("deviceType", kw.get("device_types"))
        self.ds.set_user_prop("type", kw.get("device_types"))
        redirect("/ocip")

    @expose('reqaid.templates.ocipsettings')
    def ocipsettings(self, **kw):
        kw["page"] = "ocipsettings"
        if kw.get("action") == "set_admin":
            kw["admin_username"] = ''
            kw["admin_password"] = ''
        elif kw.get("action") == "set_device_type":
            kw["device_types"] = self.ds.get_device_types()
        log.debug("[OCIP] open ocipsettings.xhtml with (%s)" % kw)
        return kw

    def _has_settings(self, *args):
        for p in args:
            v = self.ds.get_user_prop(p)
            print "********* %s:%s" % (p,v)
            if v == '':
                print "***** return False"
                return False
        print "***** return True"
        return True

    @expose('reqaid.templates.ociprequest')
    def index(self):
        log.debug("[OCIP] index")
        if not self._has_settings("admin_username", "admin_password"):
            redirect("ocip/ocipsettings", action="set_admin")
        elif not self._has_settings("deviceType"):
            redirect("ocip/ocipsettings", action="set_device_type")
        return self.base_dict
