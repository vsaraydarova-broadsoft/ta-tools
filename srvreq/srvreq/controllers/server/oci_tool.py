import time
from xml.etree.ElementTree import Element
from xml.etree.ElementTree import SubElement
import xml.etree.ElementTree as Etree
import hashlib
import random
import string
from utils import value_to_str
from suds.client import Client
from robot.api import logger


class OciClient:
    """
    Simple OCI-P SOAP Client.
    """

    def __init__(self, username, password, xsp, override_location=False):
        """
        :param username: OCI-P username. Typically a group admin username.
        :param password: OCI-P password
        :param xsp: XSP root url
        :param override_location: When 'True' generates service location
                                  using parameter 'xsp', instead of using
                                  the default service location from WSDL.

        """
        self.username = username
        self.password = password
        self.session_id = hashlib.sha1("UC-ONE UI Test OCI-P SOAP:%s:%s" %
                                       (random.randint(1, 1000000000),
                                        time.time())).hexdigest()
        self.wsdl_url = "%s/webservice/services/ProvisioningService?wsdl" % \
                        xsp
        location = ("%s/webservice/services/ProvisioningService" % xsp) \
            if override_location else None
        self.oci_soap = Client(self.wsdl_url, location=location)
        auth_reponse = Etree.fromstring(self.authentication_request())
        self.nonce = auth_reponse.find('.//nonce').text
        self.login_request()

    def _oci_xml(self, cmd, *cmd_elements):
        """
        Generates OCI-P requests XML.

        Basic structure of OCI-P request XML is as follows:

        <?xml version="1.0" encoding="ISO-8859-1"?>
        <BroadsoftDocument protocol = "OCI" xmlns="C"
                 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
            <sessionId xmlns="">UI aut Oci client 1459925817.42</sessionId>
            <command xsi:type="AuthenticationRequest" xmlns="">
                <userId>admin@domain.com</userId>
            </command>
        </BroadsoftDocument>

        :param cmd: OCI-P requests command type
        :param cmd_elements: Elements which are added under "command" node in
                             generated OCI requests xml. Added elements are
                             defined as key value pairs so that key represents
                             the name of the added sub element, and value
                             represents its value.
        :return: OCI-P requests xml document
        """
        root = Element('BroadsoftDocument',
                       attrib={'protocol': 'OCI', 'xmlns': 'C',
                               'xmlns:xsi': 'http://www.w3.org/2001/'
                                            'XMLSchema-instance'})
        session = SubElement(root, 'sessionId', attrib={'xmlns': ''})
        session.text = self.session_id
        command = SubElement(root, 'command',
                             attrib={'xsi:type': cmd, 'xmlns': ''})
        for elem in cmd_elements:
            parent = None
            if 'parent' in elem:
                parent = elem.pop('parent')
            cmd_element = Element(elem.items()[0][0])
            if elem.items()[0][1] is not None:
                if len(elem.items()[0][1]) == 0:
                    cmd_element.set("xsi:nil", "true")
                else:
                    cmd_element.text = elem.items()[0][1]
            if parent is not None:
                command.find(parent).append(cmd_element)
            else:
                command.append(cmd_element)
        ret = '<?xml version="1.0" encoding="ISO-8859-1"?>%s' % \
              (Etree.tostring(root))
        return ret

    def _group_requests(self, cmd, *cmd_elements, **kwargs):
        """
        Process group level oci request. Automatically adds default
        service provider id and group id to the request.

        :param cmd:           See documentation of def _send()
        :param cmd_elements:  See documentation of def _send()
        :param kwargs:        group_id
                                If present, overrides the default group_id
                              service_provider_id
                                If present, overrides the default
                                service_provider_id.
        :return:  See documentation of  def _send()
        """
        service_provider = {'serviceProviderId':
                            kwargs.get('service_provider_id',
                                       self.service_provider)}
        group = {'groupId': kwargs.get('group_id', self.group)}
        return self._send(self._oci_xml(cmd, service_provider, group,
                                        *cmd_elements))

    def _send(self, oci_command):
        """
        Process one OCI-P SOAP transaction.

        :param oci_command: OCI requests xml
        :return: OCI response xml
        """
        logger.trace(oci_command)
        response = self.oci_soap.service.processOCIMessage(oci_command)
        if response:
            logger.trace(response)
            response_cmd = Etree.fromstring(response).find('.//command')
            if response_cmd is not None and response_cmd.get('type'):
                assert response_cmd.get('type') != 'Error', \
                    "Error response received\n" \
                    "OCI Command: \n%s\n" \
                    "OCI Response:\n%s\n" % (oci_command, response)
            return response

    def authentication_request(self):
        """
        Authenticates (AuthenticationRequest) user. First step in OCI-P
        SOAP two phase authentication.

        :return: OCI response xml
        """
        response = self._send(self._oci_xml('AuthenticationRequest',
                                            {'userId': self.username}))
        parsed_response = Etree.fromstring(response)
        self.nonce = parsed_response.find('.//nonce').text
        return response

    def login_request(self):
        """
        Performs 'LoginRequest14sp4' for user. Second step in OCI-P two
        phase authentication.

        :return: OCI response xml
        """
        admin_username = {'userId': self.username}
        signed_password = {'signedPassword': _digest_pwd(self.password,
                                                         self.nonce)}
        response = self._send(self._oci_xml('LoginRequest14sp4',
                                            admin_username, signed_password))
        parsed_response = Etree.fromstring(response)
        self.service_provider = \
            parsed_response.findtext('.//serviceProviderId')
        self.group = parsed_response.findtext('.//groupId')
        return response

    def logout_request(self):
        admin_username = {'userId': self.username}
        return self._send(self._oci_xml('LogoutRequest',
                                        admin_username))

    def user_get_network_conferencing_request(self, user_id):
        user = {'userId': user_id}
        return self._send(self._oci_xml('UserNetworkConferencingGetRequest',
                                        user))

    def user_get_assigned_services(self, user_id):
        user = {'userId': user_id}
        services = {}
        parsed_response = Etree.fromstring(
                self._send(
                        self._oci_xml('UserServiceGetAssignmentListRequest',
                                      user)))
        services_table = parsed_response.find(
                './/userServicesAssignmentTable')
        rows = services_table.findall('row')
        for row in rows:
            services[row[0].text] = row[1].text.lower() == 'true'
        return services

    def user_assign_service(self, user_id, *services):
        user = {'userId': user_id}
        services_list = []
        for service in services:
            services_list.append({'serviceName': service})
        return self._send(self._oci_xml('UserServiceAssignListRequest',
                                        user, *services_list))

    def user_unassign_service(self, user_id, *services):
        user = {'userId': user_id}
        services_list = []
        for service in services:
            services_list.append({'serviceName': service})
        return self._send(self._oci_xml('UserServiceUnassignListRequest',
                                        user, *services_list))

    def user_get_security_classification(self, user_id):
        user = {'userId': user_id}
        response = self._send(self._oci_xml(
                'UserSecurityClassificationGetRequest', user))
        parsed_response = Etree.fromstring(response)
        sec_clas_elem = parsed_response.find('.//securityClassification')
        if sec_clas_elem is not None:
            ret = sec_clas_elem.text
        else:
            ret = "Unclassified"
        return ret

    def user_set_security_classification(self, user_id, security_level):
        user = {'userId': user_id}
        if security_level == "Unclassified":
            sec_level = {'securityClassification': ''}
        else:
            sec_level = {'securityClassification': security_level}
        return self._send(self._oci_xml(
                'UserSecurityClassificationModifyRequest', user, sec_level))

    def user_set_integrated_imp(self, user_id, is_active):
        return self._send(
            self._oci_xml('UserIntegratedIMPModifyRequest',
                          {'userId': user_id},
                          {'isActive': value_to_str(is_active)}))

    def user_set_no_answer_number_of_rings(self, user_id, rings):
        return self._send(
            self._oci_xml('UserVoiceMessagingUserModifyGreetingRequest20',
                          {'userId': user_id},
                          {'noAnswerNumberOfRings': str(rings)}))

    def user_set_voice_management(self, user_id, is_active, **kwargs):
        return self._send(
            self._oci_xml('UserVoiceMessagingUserModifyVoiceManagementRequest',
                          {'userId': user_id},
                          {'isActive': value_to_str(is_active)},
                          {'alwaysRedirectToVoiceMail': value_to_str(
                              kwargs.get('alwaysRedirectToVoiceMail',
                                         'false'))},
                          {'busyRedirectToVoiceMail': value_to_str(
                              kwargs.get('busyRedirectToVoiceMail', 'true'))},
                          {'noAnswerRedirectToVoiceMail': value_to_str(
                              kwargs.get('noAnswerRedirectToVoiceMail',
                                         'true'))}
                          )
        )

    def group_device_get_custom_tags(self, device_name, **kwargs):
        ret = {}
        device = {'deviceName': device_name}
        etree = Etree.fromstring(self._group_requests(
                'GroupAccessDeviceCustomTagGetListRequest',
                device, **kwargs))
        for row in etree.findall('.//row'):
            cols = [e.text for e in row.findall('col')]
            ret[cols[0]] = cols[1]
        return ret

    def group_device_add_custom_tag(self, device_name, tag, value, **kwargs):
        device = {'deviceName': device_name}
        tag = {'tagName': tag}
        value = {'tagValue': value_to_str(value)}
        return self._group_requests(
                'GroupAccessDeviceCustomTagAddRequest', device, tag, value,
                **kwargs)

    def group_device_delete_custom_tag(self, device_name, tag, **kwargs):
        device = {'deviceName': device_name}
        tag = {'tagName': tag}
        return self._group_requests(
                'GroupAccessDeviceCustomTagDeleteListRequest', device, tag,
                **kwargs)

    def group_device_modify_config_file(
            self, device_name, config_mode="Default", file_content='',
            file_format="config.xml", extended_capture=False, **kwargs):
        args = [{'deviceName': device_name},
                {'fileFormat': file_format},
                {'fileSource': config_mode}]  # 'Default'|'Manual'|'Custom'
        if file_content:
            args += [{'uploadFile': None},
                     {'fileContent': file_content,
                      'parent': 'uploadFile'}]  # xs:base64Binary
        args += [{'extendedCaptureEnabled': value_to_str(extended_capture)}]
        return self._group_requests(
            'GroupAccessDeviceFileModifyRequest14sp8', *args,
            **kwargs)

    def group_device_rebuild_config_file(self, device_name, **kwargs):
        device = {'deviceName': device_name}
        return self._group_requests(
                'GroupCPEConfigRebuildDeviceConfigFileRequest', device,
                **kwargs)

    def user_add(self, user_id, last_name, first_name, password,
                 clid_last_name=None, clid_first_name=None,
                 phone_number=None, **kwargs):
        if not clid_last_name:
            clid_last_name = last_name
        if not clid_first_name:
            clid_first_name = first_name
        if not phone_number:
            phone_number = self.group_get_available_numbers(**kwargs)[0]
        extension = phone_number[-4:]
        self._group_requests('UserAddRequest17sp4',
                             {'userId': user_id},
                             {'lastName': last_name},
                             {'firstName': first_name},
                             {'callingLineIdLastName': clid_last_name},
                             {'callingLineIdFirstName': clid_first_name},
                             {'phoneNumber': phone_number},
                             {'extension': extension},
                             {'password': password},
                             **kwargs)
        added_user = self.user_get_data(user_id)
        logger.info("Added a new user:\n%s" % added_user)
        return added_user

    def user_get(self, user_id):
        user = {'userId': user_id}
        return self._send(self._oci_xml('UserGetRequest21', user))

    def user_get_data(self, user_id):
        user_data = Etree.fromstring(self.user_get(user_id))
        ret = {'userId': user_id}
        for field in _user_data_field_names():
            value = user_data.findtext('.//%s' % field)
            if value is not None:
                ret[field] = value
        return ret

    def user_get_primary_device(self, user_id):
        user_data = Etree.fromstring(self.user_get(user_id))
        end_point = user_data.find('.//accessDeviceEndpoint')
        if end_point is not None:
            lp = end_point.findtext('linePort')
            dn = end_point.findtext('accessDevice/deviceName')
            access_device = self.group_access_device_get(dn)
            access_device['line_port'] = lp
            access_device['device_name'] = dn
            return access_device
        else:
            return None

    def user_delete(self, user_id):
        self._send(self._oci_xml('UserDeleteRequest', {'userId': user_id}))
        logger.info("User '%s' deleted." % user_id)

    def activate_imp(self, user_id, is_activate="true"):
        return self._send(
                self._oci_xml('UserIntegratedIMPModifyRequest',
                              {'userId': user_id},
                              {'isActive': is_activate}))

    def group_get_available_numbers(self, **kwargs):
        response = self._group_requests(
                'GroupDnGetAvailableListRequest', **kwargs)
        parsed_response = Etree.fromstring(response)
        dn_list = []
        for item in parsed_response.findall('.//phoneNumber'):
            dn_list.append(item.text)
        logger.info("Available numbers: %s" % dn_list)
        return dn_list

    def activate_number(self, phone_number, **kwargs):
        logger.info("Activate number %s" % phone_number)
        return self._group_requests(
                'GroupDnActivateListRequest', {'phoneNumber': phone_number},
                **kwargs)

    def group_access_device_add(self, device_name, device_type,
                                user_name, password, **kwargs):
        logger.info("Add access device. Name: %s, Device type: %s" %
                    (device_name, device_type))
        return self._group_requests('GroupAccessDeviceAddRequest14',
                                    {'deviceName': device_name},
                                    {'deviceType': device_type},
                                    {'useCustomUserNamePassword': "true"},
                                    {'accessDeviceCredentials': None},
                                    {'userName': user_name,
                                     'parent': 'accessDeviceCredentials'},
                                    {'password': password,
                                     'parent': 'accessDeviceCredentials'},
                                    **kwargs)

    def group_access_device_get(self, device_name, **kwargs):
        response = Etree.fromstring(
                 self._group_requests('GroupAccessDeviceGetRequest18sp1',
                                      {'deviceName': device_name},
                                      **kwargs))
        return {'device_type': response.findtext('.//deviceType'),
                'user_name': response.findtext('.//userName')}

    def group_access_device_delete(self, device_name, **kwargs):
        logger.info("Delete Access Device '%s'" % device_name)
        return self._group_requests('GroupAccessDeviceDeleteRequest',
                                    {'deviceName': device_name},
                                    **kwargs)

    def user_sca_get(self, user_id):
        sca = self._send(
                self._oci_xml('UserSharedCallAppearanceGetRequest21sp1',
                              {'userId': user_id}))
        logger.info(sca)
        return sca

    def user_sca_modify(self, user_id, allow_call_retrieve=True,
                        alert_all_for_click_to_dial_calls=False):
        return self._send(
                self._oci_xml('UserSharedCallAppearanceModifyRequest',
                              {'userId': user_id},
                              {'alertAllAppearancesForClickToDialCalls':
                               value_to_str(
                                       alert_all_for_click_to_dial_calls)},
                              {'allowSCACallRetrieve':
                               value_to_str(allow_call_retrieve)}))

    def user_sca_endpoint_add(self, user_id, access_device, line_port,
                              is_active=True, allow_origination=True,
                              allow_termination=True):
        logger.info("Add SCA. User: %s, Access Device: %s, Line Port: %s"
                    % (user_id, access_device, line_port))
        return self._send(
                self._oci_xml('UserSharedCallAppearance'
                              'AddEndpointRequest14sp2',
                              {'userId': user_id},
                              {'accessDeviceEndpoint': None},
                              {'accessDevice': None,
                               'parent': 'accessDeviceEndpoint'},
                              {'deviceLevel': 'Group',
                               'parent': 'accessDeviceEndpoint/'
                                         'accessDevice'},
                              {'deviceName': access_device,
                               'parent': 'accessDeviceEndpoint/'
                                         'accessDevice'},
                              {'linePort': line_port,
                               'parent': 'accessDeviceEndpoint'},
                              {'isActive': value_to_str(is_active)},
                              {'allowOrigination': value_to_str(
                                      allow_origination)},
                              {'allowTermination': value_to_str(
                                      allow_termination)}))

    def user_sca_endpoint_get(self, user_id, access_device, line_port):
        return self._send(
                self._oci_xml('UserSharedCallAppearance'
                              'GetEndpointRequest',
                              {'userId': user_id},
                              {'accessDeviceEndpoint': None},
                              {'accessDevice': None,
                               'parent': 'accessDeviceEndpoint'},
                              {'deviceLevel': 'Group',
                               'parent': 'accessDeviceEndpoint/'
                                         'accessDevice'},
                              {'deviceName': access_device,
                               'parent': 'accessDeviceEndpoint/'
                                         'accessDevice'},
                              {'linePort': line_port,
                               'parent': 'accessDeviceEndpoint'}))

    def user_sca_endpoint_delete(self, user_id, access_device, line_port):
        logger.info("Delete SCA. User: %s, Access Device: %s, Line Port: %s"
                    % (user_id, access_device, line_port))
        return self._send(
                self._oci_xml('UserSharedCallAppearance'
                              'DeleteEndpointListRequest14',
                              {'userId': user_id},
                              {'accessDeviceEndpoint': None},
                              {'accessDevice': None,
                               'parent': 'accessDeviceEndpoint'},
                              {'deviceLevel': 'Group',
                               'parent': 'accessDeviceEndpoint/'
                                         'accessDevice'},
                              {'deviceName': access_device,
                               'parent': 'accessDeviceEndpoint/'
                                         'accessDevice'},
                              {'linePort': line_port,
                               'parent': 'accessDeviceEndpoint'}))

    def user_get_sca_list(self, user_id):
        """
        Returns list of devices provisioned for given user as Shared
        Call Appearance devices.
        """
        ret = []
        response = Etree.fromstring(self._send(self._oci_xml(
                'UserSharedCallAppearanceGetRequest16sp2',
                {'userId': user_id})))
        keys = [h.text for h in response.findall('.//colHeading')]
        rows = response.findall('.//row')
        for row in rows:
            device = {}
            values = [t.text for t in row.findall('col')]
            for i in range(len(values)):
                device[keys[i]] = values[i]
            ret.append(device)
        logger.info("User '%s' SCA Devices:" % user_id)
        logger.info(ret)
        return ret

    def user_delete_all_sca_devices(self, user_id, **kwargs):
        """
        Removes all devices provisioned for given user as Shared
        Call Appearance devices. Also delete access devices.
        """
        sca_devices = self.user_get_sca_list(user_id)
        for sca_device in sca_devices:
            self.user_sca_endpoint_delete(user_id,
                                          sca_device['Device Name'],
                                          sca_device['Line/Port'])
            self.group_access_device_delete(sca_device['Device Name'],
                                            **kwargs)

    def user_primary_endpoint_add(self, user_id, access_device, line_port):
        logger.info("Add Primary Endpoint. User: %s, Access Device: %s, "
                    "Line Port: %s" % (user_id, access_device, line_port))
        return self._send(
                self._oci_xml('UserModifyRequest17sp4',
                              {'userId': user_id},
                              {'endpoint': None},
                              {'accessDeviceEndpoint': None,
                               'parent': 'endpoint'},
                              {'accessDevice': None,
                               'parent': 'endpoint/accessDeviceEndpoint'},
                              {'deviceLevel': 'Group',
                               'parent': 'endpoint/'
                                         'accessDeviceEndpoint/'
                                         'accessDevice'},
                              {'deviceName': access_device,
                               'parent': 'endpoint/'
                                         'accessDeviceEndpoint/'
                                         'accessDevice'},
                              {'linePort': line_port,
                               'parent': 'endpoint/accessDeviceEndpoint'}))

    def user_primary_endpoint_delete(self, user_id):
        logger.info("Delete user '%s' primary endpoint" % user_id)
        return self._send(
                self._oci_xml('UserModifyRequest17sp4',
                              {'userId': user_id},
                              {'endpoint': ""}))

    def user_delete_all_devices(self, user_id, **kwargs):
        logger.info("Deleting all devices of '%s'" % user_id)
        primary_device = self.user_get_primary_device(user_id)
        if primary_device is not None:
            self.user_primary_endpoint_delete(user_id)
            self.group_access_device_delete(
                    primary_device['device_name'], **kwargs)
        self.user_delete_all_sca_devices(user_id, **kwargs)

    def provision_user_with_devices(self, user_id, primary_device_type=None,
                                    sca_device_types=[], **kwargs):
        """
        Provision given user with given Identity/Device Profile types
        Before provisioning new devices, removes user's all current devices.

        :param user_id: User to be provisioned
        :param primary_device_type: Identity/Device Profile Type name of
                                    primary device to be provisioned
        :param sca_device_types: List of Identity/Device Profile Type names
                                 of devices to be provisioned as Shared Call
                                 Appearance Devices.
        :param kwargs: See _group_requests() for documentation
        """

        def generate_device_prefix(dev_type):
            initials = ''.join([w[0] for w in dev_type.lower().split(' ')])
            rnd = random.randint(0, 100)
            return '%s%s_' % (initials, rnd)

        self.user_delete_all_devices(user_id, **kwargs)
        domain = user_id.split('@')[-1]
        userpart = user_id.split('@')[0]
        if primary_device_type is not None:
            prefix = generate_device_prefix(primary_device_type)
            access_device = "%s%s" % (prefix, userpart)
            line_port = "lp_%s%s@%s" % (prefix, userpart, domain)
            self.group_access_device_add(access_device, primary_device_type,
                                         access_device,
                                         _bw_qualified_password(), **kwargs)
            self.user_primary_endpoint_add(user_id, access_device, line_port)
        for sca_device_type in sca_device_types:
            prefix = generate_device_prefix(sca_device_type)
            access_device = "%s%s" % (prefix, userpart)
            line_port = "lp_%s%s@%s" % (prefix, userpart, domain)
            self.group_access_device_add(access_device, sca_device_type,
                                         access_device,
                                         _bw_qualified_password(), **kwargs)
            self.user_sca_endpoint_add(user_id, access_device, line_port)

    def delete_user_and_devices(self, user_id, **kwargs):
        """
        Delete given user and all access devices associated with the user
        :param user_id: User to be deleted
        """
        self.user_delete_all_devices(user_id, **kwargs)
        self.user_delete(user_id)

    def group_get_assigned_domains(self, **kwargs):
        """
        Returns a list of domains assigned to the group. Group's
        default domain is the first item on the returned list.

        :return: List of domains assigned to the group.
        """
        response = Etree.fromstring(
                self._group_requests('GroupDomainGetAssignedListRequest',
                                     **kwargs))
        default_domain = response.findtext('.//groupDefaultDomain')
        domains = [d.text for d in response.findall('.//domain')]
        domains.insert(0, default_domain)
        logger.info("Available domains: '%s'" % domains)
        return domains

    def create_ucone_test_user(self, first_name, last_name, password,
                               primary_device='Polycom-550',
                               sca_devices=['Business Communicator - PC',
                                            'Business Communicator - Mobile',
                                            'Business Communicator - Tablet',
                                            'Connect - Mobile',
                                            'Iris Messenger - Mobile'],
                               clid_suffix='', **kwargs):
        """
        Create a new test user to default group in default enterprise. User
        is assigned a phone number which is also activated.
        User can also be provisioned with a primary device as well as with
        a desired list of SCA devices.

        :param first_name:      Test user's first name
        :param last_name:       Test user's last name
        :param password:        Test user's initial XSi password
        :param primary_device:  Identity/Device profile type name of desired
                                primary device. If None, primary device is
                                not provisioned.
        :param sca_devices:     List of Identity/Device profile type names of
                                desired SCA devices. If empty list, SCA
                                devices are not provisioned.
        :param clid_suffix:     Optional string that is concatenated to
                                user's CLID first and last names.

        Example: Create user Alice Anderson with "Business Communicator - PC"
                 as primary device. No SCA devices assigned.

        create_ucone_test_user("Alice", "Andersson", "Welcom3",
                               primary_device="Business Communicator - PC",
                               sca_devices=[])

        Example: Create user Alice Anderson with "Business Communicator -
                 Mobile" as SCA device. No primary device assigned.


        create_ucone_test_user("Alice", "Andersson", "Welcom3",
                               primary_device=None,
                               sca_devices=["Business Communicator - Mobile"])


        """
        domain = self.group_get_assigned_domains(**kwargs)[0]
        user_part = ''.join([last_name, first_name]).lower().replace(' ', '')
        user_id = '%s@%s' % (user_part, domain)
        clid_last_name = "%s%s" % (last_name, clid_suffix)
        clid_first_name = "%s%s" % (first_name, clid_suffix)
        dn = self.group_get_available_numbers(**kwargs)[0]
        u = self.user_add(user_id, last_name, first_name, password,
                          clid_last_name, clid_first_name, phone_number=dn,
                          **kwargs)
        self.activate_number(dn, **kwargs)
        self.user_assign_service(user_id, "Integrated IMP")
        self.activate_imp(user_id)
        self.provision_user_with_devices(user_id, primary_device,
                                         sca_devices, **kwargs)
        self.user_sca_modify(user_id, allow_call_retrieve=True)
        return u


def _user_data_field_names():
    return ['serviceProviderId', 'groupId', 'userId', 'lastName',
            'firstName', 'callingLineIdLastName',
            'callingLineIdFirstName', 'phoneNumber', 'extension',
            'department', 'title', 'pagerPhoneNumber',
            'mobilePhoneNumber', 'emailAddress', 'yahooId',
            'addressLocation', 'address', 'countryCode',
            'nationalPrefix', 'impId']


def _digest_pwd(password, nonce):
    """
    Calculate admin user's digest password for the OCI soap session.

    :param password: Admin user's password
    :param nonce: Nonce received from 'AuthenticationRequest'
    :return: Admin user's digest password for the OCI soap session.
    """
    s1 = hashlib.sha1(password).hexdigest()
    s2 = "%s:%s" % (nonce, s1)
    s3 = hashlib.md5(s2).hexdigest()
    return s3


def _bw_qualified_password():
    """
    Generates a random password which conforms to BW DMS requirements:
       - contains uppercase letters
       - contains lowercase letters
       - contains numbers
       - contains non alphanumeric characters
       - is at least 8 characters long

    :return: Password
    """
    pwd = ''
    for charset in [string.ascii_uppercase, string.ascii_lowercase,
                    string.digits, "!#?.,"]:
        pwd = pwd + ''.join(random.choice(charset) for _ in range(3))
    return pwd


def test_create_oci_tool(username, password, xsp, override_location=False):
    """
    Used by oci_tests.robot
    """
    return OciClient(username, password, xsp, override_location)
