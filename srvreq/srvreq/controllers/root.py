# -*- coding: utf-8 -*-
"""Main Controller"""

import logging
from tg import expose, flash, require, url, lurl
from tg import request, redirect, tmpl_context
from tg.i18n import ugettext as _, lazy_ugettext as l_
from tg.exceptions import HTTPFound
from tg import predicates
from srvreq import model
from srvreq.controllers.secure import SecureController
from srvreq.model import DBSession
from tgext.admin.tgadminconfig import BootstrapTGAdminConfig as TGAdminConfig
from tgext.admin.controller import AdminController

from srvreq.lib.base import BaseController

from srvreq.controllers.error import ErrorController
from srvreq.controllers.ocip import OCIPController
from srvreq.controllers.xsi import XSIController
from srvreq.controllers.setting import SettingsController
from srvreq.controllers.trace import TraceController

from srvreq.model.setting import Setting
import srvreq.controllers.server.utils as utils


__all__ = ['RootController']

log = logging.getLogger(__name__)


class RootController(BaseController):
    """
    The root controller for the srvreq application.

    All the other controllers and WSGI applications should be mounted on this
    controller. For example::

        panel = ControlPanelController()
        another_app = AnotherWSGIApplication()

    Keep in mind that WSGI applications shouldn't be mounted directly: They
    must be wrapped around with :class:`tg.controllers.WSGIAppController`.

    """
    secc = SecureController()
    admin = AdminController(model, DBSession, config_type=TGAdminConfig)

    error = ErrorController()
    trace = TraceController()

    _settings = SettingsController()
    ocip = OCIPController(_settings)
    xsi = XSIController(_settings)

    def _before(self, *args, **kw):
        tmpl_context.project_name = "srvreq"

    def _settings_form(self, **kw):
        settings = {s.__dict__["name"]: s.__dict__["value"] \
                    for s in DBSession.query(Setting).all()}
        _dict = dict(data=settings,
                    xsp_username=self._settings.get_user_prop("xsp_username"),
                    xsp_password=self._settings.get_user_prop("xsp_password"))
        utils.update_dict(_dict, kw)
        return _dict

    def get_property_value(self, name):
        return self._settings.get_active_user_prop(name)

    def set_property_value(self, name, value):
        return self._settings.set_active_user_prop(name, value)

    @expose('srvreq.templates.settings')
    def _default(self, pagename="Settings", **kw):
        return self._settings_form(**kw)

    @expose('srvreq.templates.settings')
    def settings(self, **kw):
        dict = self._settings_form(**kw)
        dict["page"] = 'settings'
        return dict

    @expose('srvreq.templates.index')
    def index(self):
        """Handle the front-page."""
        return dict(page='index')
    @expose('srvreq.templates.about')
    def about(self):
        """Handle the 'about' page."""
        return dict(page='about')

    @expose('srvreq.templates.environ')
    def environ(self):
        """This method showcases TG's access to the wsgi environment."""
        return dict(page='environ', environment=request.environ)

    @expose('srvreq.templates.data')
    @expose('json')
    def data(self, **kw):
        """
        This method showcases how you can use the same controller
        for a data page and a display page.
        """
        return dict(page='data', params=kw)
    @expose('srvreq.templates.index')
    @require(predicates.has_permission('manage', msg=l_('Only for managers')))
    def manage_permission_only(self, **kw):
        """Illustrate how a page for managers only works."""
        return dict(page='managers stuff')

    @expose('srvreq.templates.index')
    @require(predicates.is_user('editor', msg=l_('Only for the editor')))
    def editor_user_only(self, **kw):
        """Illustrate how a page exclusive for the editor works."""
        return dict(page='editor stuff')

    @expose('srvreq.templates.login')
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
        flash(_('Welcome back, %s!') % userid)

        # Do not use tg.redirect with tg.url as it will add the mountpoint
        # of the application twice.
        return HTTPFound(location=came_from)

    @expose()
    def post_logout(self, came_from=lurl('/')):
        """
        Redirect the user to the initially requested page on logout and say
        goodbye as well.

        """
        flash(_('We hope to see you soon!'))
        return HTTPFound(location=came_from)
