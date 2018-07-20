# -*- coding: utf-8 -*-
"""Sample controller with all its actions protected."""
import logging
import transaction
from tg import expose, redirect, flash
from tg.i18n import ugettext as _, lazy_ugettext as l_
from srvreq.model import DBSession
from srvreq.model.user import XSPUser
from srvreq.model.setting import Setting
from srvreq.lib.base import BaseController

import server.tools as tools
import server.utils as utils

__all__ = ['SettingsController']

log = logging.getLogger(__name__)

class SettingsController(BaseController):

    user_data = {}

    def __init__(self):
        self.user_data["xsp_username"] = DBSession.query(Setting).filter_by(name="xsp_username").first().value
        self.user_data["xsp_password"] = DBSession.query(Setting).filter_by(name="xsp_password").first().value
        self.user_data["deviceType"] = DBSession.query(Setting).filter_by(name="device_type").first().value

    def get_user(self):
        return self.user_data.get("name", '')

    def get_user_data(self):
        return self.user_data

    def get_server(self):
        return DBSession.query(Setting).filter_by(name="oci_root").one().value

    def get_admin_username(self):
        return DBSession.query(Setting).filter_by(name="admin_username").one().value

    def get_admin_password(self):
        return DBSession.query(Setting).filter_by(name="admin_password").one().value

    def get_device_type(self):
        self.user_data["deviceType"] = DBSession.query(Setting).filter_by(
            name="device_type").one().value
        return self.user_data["deviceType"]

    def get_user_prop(self, name, default=''):
        if name in ["deviceName", "fileContent"] and name not in self.user_data.keys():
            try:
                xsi = tools.create_xsi_tool_for_account(
                    DBSession.query(Setting).filter_by(name="oci_root").one().value,
                    self.user_data)
                if name == "deviceName":
                    self.user_data["deviceName"] = xsi.get_device_name_by_type(
                        self.get_device_type())
                if name == "fileContent":
                    self.user_data["fileContent"] = utils.xml_string(
                        xsi.get_dm_config(deviceType=self.get_device_type()))
            except Exception as e:
                log.error("failed to get '%s'. %s" % (name, e))
        return self.user_data.get(name, default)

    def set_user_prop(self, name, value):
        self.user_data[name] = value

    def set_user_props(self, **kw):
        utils.update_dict(self.user_data, kw)

    @expose()
    def index(self):
        redirect('/')

    @expose()
    def save(self, **kwargs):
        log.info("<DB> Save settings %s" % kwargs)
        for k, v in kwargs.iteritems():
            DBSession.query(Setting).filter_by(name=k).one().value = v
        self.user_data["deviceType"] = kwargs.get("device_type")
        self.user_data["fetched"] = False
        redirect("/settings")

    def fetch_user_data(self, xsp_username, xsp_password):
        DBSession.query(Setting).filter_by(name="xsp_username").one().value = xsp_username
        DBSession.query(Setting).filter_by(name="xsp_password").one().value = xsp_password
        if self.user_data.get("name") != xsp_username:
            self.user_data = {}
        self.user_data["xsp_username"] = xsp_username
        self.user_data["xsp_password"] = xsp_password
        self.user_data["name"] = xsp_username
        self.user_data["fetched"] = True
        self.user_data["deviceType"] = DBSession.query(Setting).filter_by(name="device_type").first().value
        self.user_data["type"] = self.user_data["deviceType"]
        self.user_data["userId"] = xsp_username
        self.user_data["password"] = xsp_password
        server = DBSession.query(Setting).filter_by(name="oci_root").one().value
        tools.fetch_server_data(server, [self.user_data])

    @expose()
    def set_user(self, xsp_username, xsp_password):
        log.info("<DB> Add User (%s,%s)" % (xsp_username, xsp_password))
        if xsp_username and xsp_password:
            self.fetch_user_data(xsp_username, xsp_password)
            content = "%s" % self.user_data
            redirect("/settings", output=content)
        else:
            flash(_('Empty username or password'), 'error')
            redirect("/settings")