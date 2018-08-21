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

from reqaid.controllers.datastorage import DataStorage

__all__ = ['RootController']

log = logging.getLogger(__name__)


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
        try:
            self.data.fetch_user_data()
        except AssertionError as ae:
            log.error("Failed to fetch server data: %s" % ae)
            redirect('/logout_handler')
        except Exception as e:
            log.error("Failed to fetch server data: %s" % e)
            redirect('/logout_handler', params=dict(output="Failed to fetch server data: %s" % e))

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
