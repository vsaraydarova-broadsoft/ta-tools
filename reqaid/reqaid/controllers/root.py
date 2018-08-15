# -*- coding: utf-8 -*-
"""Main Controller"""

import logging
from tg import expose, flash, require, url, lurl
from tg import request, redirect, tmpl_context
from tg.i18n import ugettext as _
from tg.exceptions import HTTPFound
from reqaid import model
from reqaid.controllers.secure import SecureController
from reqaid.model import DBSession
from tgext.admin.tgadminconfig import BootstrapTGAdminConfig as TGAdminConfig
from tgext.admin.controller import AdminController

from reqaid.lib.base import BaseController
from reqaid.controllers.error import ErrorController
from reqaid.controllers.ocip import OCIPController
from reqaid.controllers.xsi import XSIController

import server.tools as tools
import server.utils as utils

__all__ = ['RootController']

log = logging.getLogger(__name__)

class DataStorage:

    def _dump_db(self):
        users = DBSession.query(model.User).all()
        log.debug("[DataStorage] DUMB Users %s", [u.user_name for u in users])
        groups = DBSession.query(model.Group).all()
        log.debug("[DataStorage] DUMB Group %s", [(g.group_name, g.users) for g in groups])

    def _dump(self, dict, description='storage'):
        log.debug("[DataStorage] DUMP %s", description)
        for k,v in dict.iteritems():
            log.debug("%s : %s" % (k, v))

    def _user(self):
        return request.identity["repoze.who.userid"]

    def get_user(self):
        return request.identity["repoze.who.userid"]

    def get_user_data(self):
        return request.identity["userdata"]

    def get_server(self):
        return self.get_user_prop("server")

    def get_admin_username(self):
        return self.get_user_prop("admin_username", default=None)

    def get_admin_password(self):
        return self.get_user_prop("admin_password", default=None)

    def fetch_user_data(self):
        user = request.identity['user']
        user_data = request.identity["userdata"]
        user_data["xsp_username"] = user.user_name
        user_data["xsp_password"] = user.password
        user_data["server"] = user.server
        user_data["name"] = user.user_name
        user_data["userId"] = user.user_name
        user_data["password"] = user.password
        tools.fetch_server_data(user.server, [user_data])

    def get_device_type(self):
        return self.get_user_prop("deviceType")

    def get_device_types(self):
        user_data = request.identity["userdata"]
        if user_data.get("deviceTypes"):
            return user_data["deviceTypes"]
        if user_data.get("admin_username") and user_data.get("admin_password"):
            oci = tools.create_oci_tool(username=user_data.get("admin_username"),
                                        password=user_data.get("admin_password"),
                                        server=user_data.get("server"))
            user_data["userSCAList"] = oci.user_get_sca_list(self._user())
            return [item['Device Type'] for item in user_data["userSCAList"]]
        return []

    def get_user_prop(self, name, default=''):
        log.debug("[DataStorage] get_user_prop %s default='%s'" % (name, default))
        user_data = request.identity["userdata"]
        if name in ["deviceName", "fileContent"] and name not in user_data.keys():
            try:
                xsi = tools.create_xsi_tool_for_account(
                    user_data["server"], user_data)
                if name == "deviceName":
                    user_data["deviceName"] = xsi.get_device_name_by_type(
                        self.get_device_type())
                if name == "fileContent":
                    user_data["fileContent"] = utils.xml_string(
                        xsi.get_dm_config(deviceType=self.get_device_type()))
            except Exception as e:
                log.error("[DataStorage] failed to get '%s'. %s" % (name, e))
        log.debug("[DataStorage] get_user_prop return %s" % user_data.get(name, default))
        return user_data.get(name, default)

    def set_user_prop(self, name, value):
        log.debug("[DataStorage] set_user_prop %s = '%s'" % (name, value))
        request.identity["userdata"][name] = value
        self._dump(request.identity["userdata"])

    def set_user_props(self, **kw):
        log.debug("[DataStorage] set_user_props %s" % kw)
        utils.update_dict(request.identity["userdata"], kw)
        self._dump(request.identity["userdata"])

    def delete_user_prop(self, name):
        log.debug("[DataStroage] delete_user_prop %s" % name)
        request.identity["userdata"].pop(name, None)

    def delete_user_props(self, *args):
        for name in args:
            log.debug("[DataStroage] delete_user_props %s" % name)
            request.identity["userdata"].pop(name, None)


class RootController(BaseController):
    """
    The root controller for the reqaid application.

    All the other controllers and WSGI applications should be mounted on this
    controller. For example::

        panel = ControlPanelController()
        another_app = AnotherWSGIApplication()

    Keep in mind that WSGI applications shouldn't be mounted directly: They
    must be wrapped around with :class:`tg.controllers.WSGIAppController`.

    """
    secc = SecureController()
    admin = AdminController(model, DBSession, config_type=TGAdminConfig)

    data = DataStorage()

    error = ErrorController()
    ocip = OCIPController(data)
    xsi = XSIController(data)

    def _before(self, *args, **kw):
        tmpl_context.project_name = ""

    @expose()
    def _default(self, pagename="Settings", **kw):
        redirect('/xsi')

    @expose('reqaid.templates.login')
    def login(self, came_from=lurl('/'), failure=None, login=''):
        """Start the user login."""
        if failure is not None:
            if failure == 'user-not-found':
                flash(_('User not found'), 'error')
            elif failure == 'invalid-password':
                flash(_('Invalid Password'), 'error')

        login_counter = request.environ.get('repoze.who.logins', 0)
        if failure is None and login_counter > 0:
            flash(_('Wrong credentials'), 'warning')

        return dict(page='login', login_counter=str(login_counter),
                    came_from=came_from, login=login)

    @expose()
    def post_login(self, came_from=lurl('/')):
        """
        Redirect the user to the initially requested page on successful
        authentication or redirect her back to the login page if login failed.

        """
        if not request.identity:
            login_counter = request.environ.get('repoze.who.logins', 0) + 1
            redirect('/login',
                     params=dict(came_from=came_from, __logins=login_counter))
        userid = request.identity['repoze.who.userid']
        self.data.fetch_user_data()

        # Do not use tg.redirect with tg.url as it will add the mountpoint
        # of the application twice.
        return HTTPFound(location=came_from)

    @expose()
    def post_logout(self, came_from=lurl('/')):
        """
        Redirect the user to the initially requested page on logout and say
        goodbye as well.

        """
        return HTTPFound(location=came_from)

    '''
    @expose('reqaid.templates.index')
    def index(self):
        """Handle the front-page."""
        return dict(page='index')
    @expose('reqaid.templates.about')
    def about(self):
        """Handle the 'about' page."""
        return dict(page='about')

    @expose('reqaid.templates.environ')
    def environ(self):
        """This method showcases TG's access to the wsgi environment."""
        return dict(page='environ', environment=request.environ)

    @expose('reqaid.templates.data')
    @expose('json')
    def data(self, **kw):
        """
        This method showcases how you can use the same controller
        for a data page and a display page.
        """
        return dict(page='data', params=kw)
    
    @expose('reqaid.templates.index')
    @require(predicates.has_permission('manage', msg=l_('Only for managers')))
    def manage_permission_only(self, **kw):
        """Illustrate how a page for managers only works."""
       return dict(page='managers stuff')

    @expose('reqaid.templates.index')
    @require(predicates.is_user('editor', msg=l_('Only for the editor')))
    def editor_user_only(self, **kw):
       """Illustrate how a page exclusive for the editor works."""
       return dict(page='editor stuff')
    '''