# -*- coding: utf-8 -*-
"""
Global configuration file for TG2-specific settings in reqaid.

This file complements development/deployment.ini.

"""
from tg.configuration import AppConfig

import reqaid
from reqaid import model, lib

import transaction

base_config = AppConfig()
base_config.renderers = []

# True to prevent dispatcher from striping extensions
# For example /socket.io would be served by "socket_io"
# method instead of "socket".
base_config.disable_request_extensions = False

# Set None to disable escaping punctuation characters to "_"
# when dispatching methods.
# Set to a function to provide custom escaping.
base_config.dispatch_path_translator = True

base_config.prefer_toscawidgets2 = True

base_config.package = reqaid

# Enable json in expose
base_config.renderers.append('json')

# Set the default renderer
base_config.renderers.append('kajiki')
base_config['templating.kajiki.strip_text'] = False  # Change this in setup.py too for i18n to work.

base_config.default_renderer = 'kajiki'


# Configure Sessions, store data as JSON to avoid pickle security issues
base_config['session.enabled'] = True
base_config['session.data_serializer'] = 'json'
# Configure the base SQLALchemy Setup
base_config.use_sqlalchemy = True
base_config.model = reqaid.model
base_config.DBSession = reqaid.model.DBSession
# Configure the authentication backend
base_config.auth_backend = 'sqlalchemy'
# YOU MUST CHANGE THIS VALUE IN PRODUCTION TO SECURE YOUR APP
base_config.sa_auth.cookie_secret = "9950b3f1-54a0-47e0-a378-aa63f973ce9f"
# what is the class you want to use to search for users in the database
base_config.sa_auth.user_class = model.User

from tg.configuration.auth import TGAuthMetadata


# This tells to TurboGears how to retrieve the data for your user
class ApplicationAuthMetadata(TGAuthMetadata):
    def __init__(self, sa_auth):
        self.sa_auth = sa_auth

    def _add_manager(self, user, password, server):
        u = model.User(user_name=user, password=password, server=server)
        self.sa_auth.dbsession.add(u)
        g = self.sa_auth.dbsession.query(model.Group).filter_by(group_name='managers').one()
        g.users.append(u)
        self.sa_auth.dbsession.flush()
        transaction.commit()

    def _update_manager(self, user, password, server):
        self.sa_auth.dbsession.query(model.User).filter_by(
            user_name=user).one().password = password
        self.sa_auth.dbsession.query(model.User).filter_by(
            user_name=user).one().server = server
        self.sa_auth.dbsession.flush()
        transaction.commit()

    def authenticate(self, environ, identity):
        login = identity['login']
        password = identity['password']
        server = environ['webob._parsed_post_vars'][0]['server']

        user = self.sa_auth.dbsession.query(self.sa_auth.user_class).filter_by(
            user_name=login
        ).first()

        if not user:
            self._add_manager(login, password, server)
        ## elif not user.validate_password(identity['password']):
        else:
            self._update_manager(login, password, server)

        user = self.sa_auth.dbsession.query(self.sa_auth.user_class).filter_by(
            user_name=login
        ).first()

        if login is None:
            try:
                from urllib.parse import parse_qs, urlencode
            except ImportError:
                from urlparse import parse_qs
                from urllib import urlencode
            from tg.exceptions import HTTPFound

            params = parse_qs(environ['QUERY_STRING'])
            params.pop('password', None)  # Remove password in case it was there
            if user is None:
                params['failure'] = 'user-not-found'
            else:
                params['login'] = identity['login']
                params['failure'] = 'invalid-password'

            # When authentication fails send user to login page.
            environ['repoze.who.application'] = HTTPFound(
                location=environ['SCRIPT_NAME'] + '?'.join(('/login', urlencode(params, True)))
            )
        return login

    def get_user(self, identity, userid):
        return self.sa_auth.dbsession.query(self.sa_auth.user_class).filter_by(
            user_name=userid
        ).first()

    def get_groups(self, identity, userid):
        return [g.group_name for g in identity['user'].groups]

    def get_permissions(self, identity, userid):
        return [p.permission_name for p in identity['user'].permissions]

base_config.sa_auth.dbsession = model.DBSession

base_config.sa_auth.authmetadata = ApplicationAuthMetadata(base_config.sa_auth)

# In case ApplicationAuthMetadata didn't find the user discard the whole identity.
# This might happen if logged-in users are deleted.
base_config['identity.allow_missing_user'] = True

# You can use a different repoze.who Authenticator if you want to
# change the way users can login
# base_config.sa_auth.authenticators = [('myauth', SomeAuthenticator()]

# You can add more repoze.who metadata providers to fetch
# user metadata.
# Remember to set base_config.sa_auth.authmetadata to None
# to disable authmetadata and use only your own metadata providers
# base_config.sa_auth.mdproviders = [('myprovider', SomeMDProvider()]

# override this if you would like to provide a different who plugin for
# managing login and logout of your application
base_config.sa_auth.form_plugin = None

# You may optionally define a page where you want users to be redirected to
# on login:
base_config.sa_auth.post_login_url = '/post_login'

# You may optionally define a page where you want users to be redirected to
# on logout:
base_config.sa_auth.post_logout_url = '/post_logout'
'''
try:
    # Enable DebugBar if available, install tgext.debugbar to turn it on
    from tgext.debugbar import enable_debugbar
    enable_debugbar(base_config)
except ImportError:
    pass
'''
