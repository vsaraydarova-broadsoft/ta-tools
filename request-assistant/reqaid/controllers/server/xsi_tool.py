"""Utilities for interacting with XSI
"""
import requests
from requests.auth import HTTPDigestAuth
import copy
import utils


def _pc_dm_url(elem, **kwargs):
    for e in elem.findall(utils.ns_escape("accessDevice")):
        if e.find(utils.ns_escape("deviceType")).text == \
                kwargs.get("deviceType", "Business Communicator - PC"):
            return [e.find(utils.ns_escape(x)).text for
                    x in ["deviceTypeUrl",
                          "deviceUserNamePassword/userName",
                          "deviceUserNamePassword/password"]]
    assert False, "Unable to find device URL and credentials in profile XML"


def _location(params):
    e = utils.element('simRingLocation')
    for tag in ['address', 'answerConfirmationRequired']:
        utils.sub_element(e, tag, params[tag])
    return e


def _update_simultaneous_ring(tree_, state):
    tree = copy.deepcopy(tree_)
    if 'active' in state:
        tree.xpath("//*[local-name() = 'active']"
                   )[0].text = utils.bool_to_str(state['active'])
    if 'incomingCalls' in state:
        text = "Ring for all Incoming Calls"
        if state['incomingCalls']:
            text = "Do not Ring if on a Call"
        tree.xpath("//*[local-name() = 'incomingCalls']")[0].text = text
    if 'simRingLocations' not in state:  # Do not modify locations
        return tree
    e = tree.find(utils.ns_escape('simRingLocations'))
    if e is None and state['simRingLocations'] == []:
        return tree
    if e is None:
        e = utils.element('simRingLocations')
        tree.getroot().insert(2, e)
    e.clear()
    if state['simRingLocations'] == []:  # Delete locations
        e.attrib["{http://www.w3.org/2001/XMLSchema-instance}nil"] = "true"
        return tree
    for loc in state['simRingLocations']:
        e.append(_location(loc))
    return tree


def _update_forward_number(tree_, number_field_name, state):
    tree = copy.deepcopy(tree_)
    tree.xpath("//*[local-name() = 'active']")[0].text = \
        utils.bool_to_str(state["active"])
    e = tree.find(utils.ns_escape(number_field_name))
    if e is None:
        e = tree.getroot().makeelement(number_field_name)
        tree.getroot().insert(1, e)
    e.text = state["number"]
    if not state["number"]:
        # Xsi server requires this twisted way of defining an
        # empty string value
        e.attrib["{http://www.w3.org/2001/XMLSchema-instance}nil"] = "true"
    if "ringSplash" in state:
        tree.xpath("//*[local-name() = 'ringSplash']")[0].text = \
            utils.bool_to_str(state["ringSplash"])
    return tree


class XsiTool:
    def __init__(self, xsp_url, username, password):
        self.xsp_url = xsp_url
        self.username = username
        self.password = password

    def _xsi_http(self, fn, **kwargs):
        api_endpoint = kwargs.get("api_endpoint", None)
        location = kwargs.get("location", None)
        parse = kwargs.get("parse", True)
        data = kwargs.get("data", None)
        auth = kwargs.get("auth", None) or (self.username, self.password)
        url = location if location else (
            "%s/com.broadsoft.xsi-actions/v2.0"
            "/user/%s/%s" %
            (self.xsp_url, self.username, api_endpoint))
        r = fn(url, verify=True, data=data, auth=auth)
        if len(r.history) > 0 and r.history[0].is_redirect:
            # requests bug (loses authorization header when redirected)
            return self._xsi_http(
                fn,
                **utils.update_dict(kwargs, {
                    "location": r.history[0].headers["Location"]
                    }))
        assert str(r.status_code)[0] == '2', \
            "HTTP request %s failed (%s): %s" % (url,
                                                 str(r.status_code),
                                                 r.content or "")
        return utils.xml_tree(r.content) if parse else True

    def xsi_get(self, api_endpoint):
        return self._xsi_http(requests.get, api_endpoint=api_endpoint)

    def xsi_put(self, api_endpoint, data):
        return self._xsi_http(requests.put,
                              api_endpoint=api_endpoint,
                              parse=False,
                              data=data)

    def xsi_delete(self, api_endpoint):
        return self._xsi_http(requests.delete,
                              api_endpoint=api_endpoint,
                              parse=False)

    def _dm_get(self, url, username, password, **kwargs):
        ucaas = kwargs.get('ucaas', False)
        file_extension = ".xml" if not ucaas else "-uc1s.xml"
        file_name = kwargs.get("fileFormat", "config.xml").split('.')[0]
        return self._xsi_http(requests.get,
                              api_endpoint=None,
                              location=url + file_name + file_extension,
                              auth=HTTPDigestAuth(username, password))

    def get_dm_config(self, **kwargs):
        return self._dm_get(*_pc_dm_url(self.xsi_get("profile/device"),
                                        **kwargs), **kwargs)

    def get_directory_data(self):
        tree = self.xsi_get(
            "directories/enterprise?userId=%s" % self.username)
        ret = {}
        for field in [
                "firstName", "lastName", "number", "extension",
                "displayName", "emailAddress", "additionalDetails/impId",
                "bridgeId", "roomId", "groupId", "addressLine1",
                "city", "zip", "country"]:
            ret[field[field.find("/") + 1:]] = utils.node_value(
                tree,
                "enterpriseDirectory/directoryDetails/%s" % field)
        ret["jid"] = ret["impId"]
        return ret

    def get_provisioned_devices(self):
        tree = self.xsi_get("profile/device")
        return tree.xpath("//*[local-name() = 'accessDevice']"
                          "/*[local-name() = 'deviceType']/text()")

    def get_device_name_by_type(self, type):
        tree = self.xsi_get("profile/device")
        return tree.xpath("//*[local-name() = 'deviceType']"
                          "[contains(text(), '%s')]"
                          "/../*[local-name() = 'deviceName']"
                          "/text()" % type)[0]

    def get_calls(self):
        return self.xsi_get("calls")

    def _parse_call_ids(self, tree):
        return utils.node_values(tree, "call/callId")

    def _hangup_calls(self, tree):
        for call_id in self._parse_call_ids(tree):
            self.xsi_delete("calls/%s" % call_id)

    def get_conference_calls(self):
        return self.xsi_get("calls/conference")

    def hangup_calls(self):
        self._hangup_calls(self.get_calls())

    def hangup_conference_calls(self):
        self._hangup_calls(self.get_conference_calls())

    def get_call_logs(self):
        tree = self.xsi_get("directories/calllogs")
        return tree

    def delete_call_logs(self):
        self.xsi_delete("directories/calllogs")

    def _get_active_state(self, api_endpoint):
        tree = self.xsi_get(api_endpoint)
        return utils.is_truthy(utils.node_value(tree, "active"))

    def _set_active_state(self, api_endpoint, **kwargs):
        assert "enabled" in kwargs
        enabled = kwargs["enabled"]
        tree = self.xsi_get(api_endpoint)
        tree.xpath("//*[local-name() = 'active']")[0].text = \
            utils.bool_to_str(enabled)
        self.xsi_put(api_endpoint, utils.xml_string(tree))

    def _get_element_value(self, api_endpoint, element_name):
        tree = self.xsi_get(api_endpoint)
        return utils.node_value(tree, element_name)

    def _set_element_value(self, api_endpoint, element_name, element_value):
        tree = self.xsi_get(api_endpoint)
        tree.xpath("//*[local-name() = '%s']" % element_name)[0].text = \
            element_value
        self.xsi_put(api_endpoint, utils.xml_string(tree))

    def get_moh(self):
        return self._get_active_state("services/musiconhold")

    def set_moh(self, **kwargs):
        self._set_active_state("services/musiconhold", **kwargs)

    def get_dnd(self):
        tree = self.xsi_get("services/donotdisturb")
        active, splash = [utils.node_value(tree, x)
                          for x in ("active", "ringSplash")]
        return {
            "active": utils.str_to_bool(active),
            "ringSplash": utils.str_to_bool(splash)
        }

    def set_dnd(self, **kwargs):
        assert "enabled" in kwargs
        enabled = kwargs["enabled"]
        tree = self.xsi_get("services/donotdisturb")
        tree.xpath("//*[local-name() = 'active']")[0].text = \
            utils.bool_to_str(enabled)
        if "ringSplash" in kwargs:
            tree.xpath("//*[local-name() = 'ringSplash']")[0].text = \
                utils.bool_to_str(kwargs["ringSplash"])
        self.xsi_put("services/donotdisturb", utils.xml_string(tree))

    def get_call_forwarding(self, forward_type="always"):
        """Get call forwarding status for given forward type.
        Returns dict with keys 'active' (bool) and 'number' (str)
        """
        tree = self.xsi_get("services/callforwarding%s" % forward_type)
        active, number = [utils.node_value(tree, x)
                          for x in ("active", "forwardToPhoneNumber")]
        res = {
            "active": utils.str_to_bool(active),
            "number": number or ""
        }
        if forward_type == "always":
            splash = utils.node_value(tree, "ringSplash")
            res["ringSplash"] = utils.str_to_bool(splash)
        return res

    def set_call_forwarding(self, **kwargs):
        """Set given call forward type to given state.
        """
        assert all([x in kwargs for x in ("active", "number")])
        forward_type = kwargs.get("forward_type", "always")
        assert forward_type in ("always", "busy", "noanswer", "notreachable")
        tree = _update_forward_number(
            self.xsi_get("services/callforwarding%s" % forward_type),
            "forwardToPhoneNumber", kwargs)
        self.xsi_put("services/callforwarding%s" % forward_type,
                     utils.xml_string(tree))

    def remove_call_forwards(self, **kwargs):
        """Remove all call forwards defined on the server.
        """
        for forward_type in "always,busy,noanswer,notreachable".split(","):
            args = utils.update_dict(kwargs, {"forward_type": forward_type,
                                              "number": "",
                                              "active": False})
            self.set_call_forwarding(**args)

    def get_call_recording_mode(self):
        return self._get_element_value("services/callrecording",
                                       "recordingMode")

    def set_call_recording_mode(self, **kwargs):
        mode = kwargs.get("mode")
        assert mode in ("on-demand-user-start", "always-pause-resume",
                        "on-demand", "never", "always")
        self._set_element_value("services/callrecording", "recordingMode",
                                mode)

    def get_remote_office(self):
        """Get Remote Office call setting
        """
        tree = self.xsi_get("services/remoteoffice")
        active, number = [utils.node_value(tree, x)
                          for x in ("active", "remoteOfficeNumber")]
        return {
            "active": utils.str_to_bool(active),
            "number": number or ""
        }

    def set_remote_office(self, **kwargs):
        """Set remote office call setting to given state.
        """
        assert all([x in kwargs for x in ("active", "number")])
        tree = _update_forward_number(self.xsi_get("services/remoteoffice"),
                                      "remoteOfficeNumber",
                                      kwargs)
        self.xsi_put("services/remoteoffice", utils.xml_string(tree))

    def set_simultaneous_ring(self, **kwargs):
        """Set given call forward type to given state.
        """
        tree = _update_simultaneous_ring(
            self.xsi_get("services/simultaneousringpersonal"), kwargs)
        self.xsi_put("services/simultaneousringpersonal",
                     utils.xml_string(tree))

    def remove_simultaneous_ring(self):
        """Remove simultaneous ring on the server.
        """
        args = {"active": False,
                "incomingCalls": False,
                "simRingLocations": []}
        self.set_simultaneous_ring(**args)

    def get_simultaneous_ring(self, **kwargs):
        """Get Simultaneous Ring call setting.
        """
        tree = self.xsi_get("services/simultaneousringpersonal")
        active, ring = [utils.node_value(tree, x)
                        for x in ("active", "incomingCalls")]
        return {
            "active": utils.str_to_bool(active),
            "incomingCalls": (ring == "Do not Ring if on a Call"),
            "simRingLocations": map(
                lambda elem: utils.node_list(elem), tree.findall(
                    utils.ns_escape("simRingLocations/simRingLocation")))
        }

    def get_broadworks_anywhere(self):
        """Get BroadWorks Anywhere call setting.
        """
        tree = self.xsi_get("services/broadworksanywhere")
        dial, paging = [utils.node_value(tree, x)
                        for x in ("alertAllLocationsForClickToDialCalls",
                                  "alertAllLocationsForGroupPagingCalls")]
        return {
            "alertAllLocationsForClickToDialCalls": utils.str_to_bool(dial),
            "alertAllLocationsForGroupPagingCalls": utils.str_to_bool(paging),
            "locations": map(
                lambda elem: utils.node_list(elem), tree.findall(
                    utils.ns_escape("locations/location")))
        }

    def get_broadworks_anywhere_location(self, phoneNumber):
        """Get BroadWorks Anywhere location.
        """
        tree = self.xsi_get(
            "services/broadworksanywhere/location/%s" % phoneNumber)
        return utils.node_list(tree.getroot())

    def delete_broadworks_anywhere_location(self, phoneNumber):
        """Get BroadWorks Anywhere location.
        """
        return self.xsi_delete(
            "services/broadworksanywhere/location/%s" % phoneNumber)

    def remove_broadworks_anywhere(self):
        """Set Click-To-Dial flag to False and delete all locations.
        """
        tree = copy.deepcopy(self.xsi_get("services/broadworksanywhere"))
        e = tree.find(utils.ns_escape("locations"))
        if e is not None:
            for phone in tree.findall(utils.ns_escape("locations/location"
                                                      "/phoneNumber")):
                self.delete_broadworks_anywhere_location(phone.text)
            # Remove locations to be able to set click-to-dial flag to false.
            # Xsi PUT requirement "phoneNumber element must include the
            # country code element."
            e.getparent().remove(e)
        tree.xpath("//*[local-name() = 'alertAllLocationsForClickToDialCalls']"
                   )[0].text = 'false'
        self.xsi_put("services/broadworksanywhere", utils.xml_string(tree))

    def get_broadworks_mobility(self):
        """Get BroadWorks Mobility call setting.

        Returns active state and primary mobile number only.
        """
        tree = self.xsi_get("services/broadworksmobility")
        active = utils.node_value(tree, "active")
        # xpath looks more complex because can't specify default
        # namespece (without prefix) in xpath function arguments
        number = tree.xpath("/*[name()='BroadWorksMobility']"
                            "/*[name()='mobileIdentity']"
                            "/*[name()='primary'][text() = 'true']"
                            "/parent::*"
                            "/*[name()='mobileNumber']/text()")
        phone = number[0] if number else ""
        return {
            "active": utils.str_to_bool(active),
            "mobileNumber": phone
        }

    def get_anonymous_call_rejection(self):
        return self._get_active_state("services/anonymouscallrejection")

    def set_anonymous_call_rejection(self, **kwargs):
        self._set_active_state("services/anonymouscallrejection", **kwargs)

    def get_call_waiting(self):
        return self._get_active_state("services/callwaiting")

    def set_call_waiting(self, **kwargs):
        self._set_active_state("services/callwaiting", **kwargs)

    def get_automatic_callback(self):
        return self._get_active_state("services/automaticcallback")

    def set_automatic_callback(self, **kwargs):
        self._set_active_state("services/automaticcallback", **kwargs)

    def get_block_my_caller_id(self):
        return self._get_active_state("services/callinglineiddeliveryblocking")

    def set_block_my_caller_id(self, **kwargs):
        self._set_active_state("services/callinglineiddeliveryblocking",
                               **kwargs)

    def set_imp(self, **kwargs):
        self._set_active_state("services/integratedimp", **kwargs)

    def get_pn_registrations(self):
        tree = self.xsi_get("profile/PushNotificationRegistrations")
        res = []
        for e in tree.findall(utils.ns_escape("pushNotificationRegistration")):
            item = utils.node_list(e)
            item["token"] = utils.node_value(e, "deviceTokenList"
                                                "/deviceToken/token")
            res.append(item)
        return res

    def delete_pn_registration(self, id, token):
        return self.xsi_delete("profile/PushNotificationRegistrations"
                               "?registrationId=%s&token=%s" % (id, token))

    def delete_pn_registrations(self):
        tree = self.xsi_get("profile/PushNotificationRegistrations")
        for e in tree.findall(utils.ns_escape("pushNotificationRegistration")):
            self.delete_pn_registration(
                utils.node_value(e, "registrationId"),
                utils.node_value(e, "deviceTokenList/deviceToken/token"))
