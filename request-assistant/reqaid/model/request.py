
class Argument:
    def __init__(self, name, **kw):
        self.name = name
        self.value = kw.get("value", '')
        self.type = kw.get('type', 'string')
        self.pos = kw.get('pos', -1)
        self.descr = kw.get('descr', '')
        self.encode = kw.get('encode', False)
        self.optional = kw.get('optional', False)

class Request:
    def __init__(self, name, request_name, display_name, type, *args):
        self.name = name
        self.request_name = request_name
        self.display_name = display_name
        assert type in ['ocip', 'xsi']
        self.type = type
        self.arguments = []
        self.arguments.extend(args)

class OCIPRequest(Request):

    def __init__(self, name, request_name, display_name, *args):
        Request.__init__(self, name, request_name, display_name, 'ocip', *args)

class XSIRequest(Request):

    def __init__(self, name, request_name, display_name, *args):
        Request.__init__(self, name, request_name, display_name, 'xsi', *args)

def add_ocip_requests(requests, request_names):

    # used to specify the requests order
    request_names.extend(["group_device_modify_config_file",
                          "group_device_rebuild_config_file",
                          "group_device_get_custom_tags",
                          "group_device_add_custom_tag",
                          "group_device_delete_custom_tag",
                          "group_access_device_get",
                          "group_access_device_add",
                          "group_access_device_delete",
                          "group_get_assigned_domains",
                          "user_add",
                          "user_get",
                          "user_delete",
                          "user_get_data",
                          "user_get_primary_device",
                          "user_get_network_conferencing_request",
                          "user_get_assigned_services",
                          "user_get_sca_list",

                          #"user_assign_service",
                          #"user_unassign_service",
                          "user_get_security_classification",
                          #"user_set_security_classification",
                          ])

    # group_device_get_custom_tags
    requests['group_device_get_custom_tags'] = OCIPRequest(
        'group_device_get_custom_tags',
        'GroupAccessDeviceCustomTagGetListRequest',
        'Group / Get custom tags',
        Argument("deviceName", pos=1),
    )
    # group_device_add_custom_tag
    requests['group_device_add_custom_tag'] = OCIPRequest(
        'group_device_add_custom_tag',
        'GroupAccessDeviceCustomTagAddRequest',
        'Group / Add custom tag',
        Argument("deviceName", pos=0),
        Argument("tagName", pos=1),
        Argument("tagValue", pos=2)
    )
    # group_device_delete_custom_tag
    requests['group_device_delete_custom_tag'] = OCIPRequest(
        'group_device_delete_custom_tag',
        'GroupAccessDeviceCustomTagDeleteListRequest',
        'Group / Delete custom tag',
        Argument("deviceName", pos=0),
        Argument("tagName", pos=1)
    )
    # group_device_modify_config_file
    requests['group_device_modify_config_file'] = OCIPRequest(
        'group_device_modify_config_file',
        'GroupAccessDeviceFileModifyRequest14sp8',
        'Config / Modify config file',
        Argument("deviceName", pos=0),
        Argument("fileSource", value='Custom', pos=1, descr="'Default' | 'Manual' | 'Custom'"),
        Argument("fileContent", type="text", pos=2, encode=True),
        Argument("fileFormat", value='config.xml', pos=3),
        Argument("extendedCaptureEnabled", pos=4, value="false", descr="true | false")
    )
    # group_device_rebuild_config_file
    requests['group_device_rebuild_config_file'] = OCIPRequest(
        'group_device_rebuild_config_file',
        'GroupCPEConfigRebuildDeviceConfigFileRequest',
        'Config / Rebuild config file',
        Argument("deviceName", pos=0),
    )
    # access device
    requests['group_access_device_add'] = OCIPRequest(
        'group_access_device_add',
        'GroupAccessDeviceAddRequest14',
        'Group / Add access device',
        Argument("deviceName", pos=0),
        Argument("deviceType", pos=1),
        Argument("userName", pos=2),
        Argument("password", pos=3),
    )
    requests['group_access_device_get'] = OCIPRequest(
        'group_access_device_get',
        'GroupAccessDeviceGetRequest18sp1',
        'Group / Get access device',
        Argument("deviceName", pos=0),
    )
    requests['group_access_device_delete'] = OCIPRequest(
        'group_access_device_delete',
        'GroupAccessDeviceDeleteRequest',
        'Group / Delete access device',
        Argument("deviceName", pos=0),
    )
    requests['group_get_assigned_domains'] = OCIPRequest(
        'group_get_assigned_domains',
        'GroupDomainGetAssignedListRequest',
        'Group / Get assigned domains'
    )
    requests['group_get_available_numbers'] = OCIPRequest(
        'group_get_available_numbers',
        'GroupDnGetAvailableListRequest',
        'Group / Get available numbers'
    )
    requests['user_add'] = OCIPRequest(
        'user_add',
        'UserAddRequest17sp4',
        'User / Add',
        Argument("userId", pos=0),
        Argument("lastName", pos=1),
        Argument("firstName", pos=2),
        Argument("password", pos=3),
        Argument("callingLineIdLastName", pos=4, optional=True, descr="optional", value=None),
        Argument("callingLineIdFirstName", pos=5, optional=True, descr="optional", value=None),
        Argument("phoneNumber", pos=6, optional=True, descr="optional", value=None)
    )

    # functions with single user_id argument
    for name in ["user_get_network_conferencing_request",
                 "user_get_assigned_services",
                 "user_get_security_classification",
                 "user_get",
                 "user_get_data",
                 "user_get_primary_device",
                 "user_delete",
                 "user_get_sca_list"
                 ]:
        requests[name] = OCIPRequest(
            name,
            '',
            "User / %s" % name[5:].replace('_', ' ').capitalize(),
            Argument("userId", pos=0)
        )

def add_xsi_requests(requests, request_names):

    # used to specify the requests order
    request_names.extend(["get_dm_config",
                     "get_device_name_by_type",
                     "get_directory_data",
                     "get_provisioned_devices",
                     "get_calls",
                     "hangup_calls",
                     "get_call_logs",
                     "delete_call_logs",
                     "get_conference_calls",
                     "hangup_conference_calls",
                     "get_moh",
                     "set_moh",
                     "get_dnd",
                     "set_dnd",
                     #"get_call_forwarding",
                     #"set_call_forwarding",
                     #"remove_call_forwards",
                     "get_call_recording_mode",
                     #"set_call_recording_mode",
                     "get_remote_office",
                     #"set_remote_office",
                     #"get_simultaneous_ring",
                     #"set_simultaneous_ring",
                     "remove_simultaneous_ring",
                     "get_broadworks_anywhere",
                     #"get_broadworks_anywhere_location",
                     #"delete_broadworks_anywhere_location",
                     "remove_broadworks_anywhere",
                     "get_broadworks_mobility",
                     "get_anonymous_call_rejection",
                     "set_anonymous_call_rejection",
                     "get_call_waiting",
                     "set_call_waiting",
                     "get_automatic_callback",
                     "set_automatic_callback",
                     "get_block_my_caller_id",
                     "set_block_my_caller_id",
                     "set_imp",
                     "get_pn_registrations",
                     #"delete_pn_registration",
                     "delete_pn_registrations",
                     ])

    requests['get_device_name_by_type'] = XSIRequest(
        'get_device_name_by_type',
        'profile/device',
        'Get device name by type',
        Argument("type", pos=0),
    )
    requests['get_dm_config'] = XSIRequest(
        'get_dm_config',
        'profile/device',
        'Get config file',
        Argument("deviceType", pos=-1),
    )
    requests['set_dnd'] = XSIRequest(
        'set_dnd',
        'profile/device',
        'Set dnd',
        Argument("enabled", type="bool", pos=-1, value={"checked": "off"}),
        Argument("ringSplash", type="bool", pos=-1, value={"checked": "off"})
    )
    # functions without arguments
    for name in ["set_moh",
                 "set_anonymous_call_rejection",
                 "set_call_waiting",
                 "set_automatic_callback",
                 "set_block_my_caller_id",
                 "set_imp",]:
        requests[name] = XSIRequest(
            name,
            '',
            name.replace('_', ' ').capitalize(),
            Argument("enabled", type="bool", pos=-1, value={"checked":"on"})
        )
    # functions without arguments
    for name in ["get_directory_data",
                 "get_provisioned_devices",
                 "get_calls",
                 "get_conference_calls",
                 "hangup_calls",
                 "hangup_conference_calls",
                 "get_call_logs",
                 "delete_call_logs",
                 "get_call_recording_mode",
                 "get_remote_office",
                 "remove_simultaneous_ring",
                 "get_broadworks_anywhere",
                 "remove_broadworks_anywhere",
                 "get_broadworks_mobility",
                 "get_anonymous_call_rejection",
                 "get_call_waiting",
                 "get_automatic_callback",
                 "get_block_my_caller_id",
                 "get_pn_registrations",
                 "delete_pn_registrations",
                 "get_moh",
                 "get_dnd"]:
        requests[name] = XSIRequest(
            name,
            '',
            name.replace('_', ' ').capitalize())