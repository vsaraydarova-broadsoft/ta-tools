import logging
from tg import request
from reqaid import model
from reqaid.model import DBSession

import server.tools as tools
import server.utils as utils

__all__ = ['DataStorage']

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
