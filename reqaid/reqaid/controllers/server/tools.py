"""
Tools for interacting with servers (Xsi, XMPP, runner_manager)
"""
import io
import copy
import json
import base64
from ConfigParser import ConfigParser
import xsi_tool
import xmpp_tool
import oci_tool
import utils
#from ..data import SERVER, ACCOUNTS

def create_xsi_tool_for_account(server, account):
    return xsi_tool.XsiTool(server,
                            account["xsp_username"],
                            account["xsp_password"])


def create_xmpp_tool_for_account(account):
    return xmpp_tool.XmppTool(account["xmpp_username"],
                              account["xmpp_password"])


def create_oci_tool(**kwargs):
    assert all([x in kwargs for x in ("username", "password", "server")]), \
        "Missing OCI setting"
    return oci_tool.OciClient(
        kwargs.get("username"),
        kwargs.get("password"),
        kwargs.get("url", kwargs.get("server")),
        kwargs.get("override_location", True))


def fetch_server_data_for_account(server, account, ucaas=False):
    xsi = create_xsi_tool_for_account(server, account)
    utils.update_dict(account, xsi.get_directory_data())
    kwargs = {"ucaas": ucaas}
    account["dm_config"] = xsi.get_dm_config(**kwargs)
    if not ucaas:
        for x in ["username", "password"]:
            account["xmpp_" + x] = utils.node_value(account["dm_config"],
                                                    "protocols/xmpp/"
                                                    "credentials/%s" % x)
        xmpp = create_xmpp_tool_for_account(account)
        utils.update_dict(account, xmpp.get_xmpp_data())


def fetch_server_data(server, accounts):
    """
    Fetch Xsi directory data, xmpp roster and localstore
    contacts for given users' accounts
    """
    for account in accounts:
        fetch_server_data_for_account(server, account)
    print accounts

#-----------------------------------------------------------------


def _apply_dm_change(tree, key, value):
    """Apply given change to XML tree

    Our syntax is not actual XPath or compatible with etree's limited
    XPath support. We support:

    1. setting node value with name
       e.g. "a/b/c", "val" (changes text of node 'c')
    2. setting attribute value
       e.g. "a/b/c/@p" "val" (changes param 'p' value of node 'c')
    """
    import lxml.etree as et
    ret = copy.deepcopy(tree)
    items = key.split("/")
    attrib_key = ""
    if items[-1][0] == "@":
        attrib_key = items[-1][1:]
        items.pop(-1)

    node = ret
    while items:
        tmp = node.find(utils.ns_escape(items[0]))
        if tmp is None:
            tmp = et.Element(items[0])
            if isinstance(node, et._ElementTree):
                node.getroot().append(tmp)
            else:
                node.append(tmp)
        node = tmp
        items.pop(0)

    if attrib_key:
        node.attrib[attrib_key] = value
    else:
        ret.find(utils.ns_escape(key)).text = value
    return ret


def _apply_dm_changes(tree, changes):
    """Apply multiple changes to the XML tree

    See \`Apply dm change\` for the path manipulation syntax help"""
    ret = copy.deepcopy(tree)
    for k, v in changes.iteritems():
        ret = _apply_dm_change(ret, k, v)
    return ret


class IniParser(ConfigParser):
    def __init__(self):
        ConfigParser.__init__(self)
        self.optionxform = str

    def to_string(self):
        b = io.BytesIO()
        self.write(b)
        b.seek(0)
        return b.read()


def create_app_ini(config):
    """
    Creates application_setting.ini content from given config

    Config is a dictionary and keys are specified in path format,
    e.g "section/item"
    """
    c = IniParser()
    for k, v in config.iteritems():
        items = k.split("/")
        section = items[0]
        if section not in c.sections():
            c.add_section(section)
        c.set(section, items[1], v)
    return c.to_string()


def apply_ini_changes(ini_contents, changes):
    """
    Apply dict of changes to given application INI contents,
    returning new contents
    """
    c = IniParser()
    c.readfp(io.BytesIO(ini_contents))

    for k, v in changes.iteritems():
        items = k.split("/")
        section = items[0]
        c.set(section, items[1], v)
    return c.to_string()


def set_dm_config_value(user, key, value, prop="dm_config"):
    """Sets a DM config value for given user's client

    *Note*: Sets in-memory config value only. \`Deploy dm changes\`
    must to be called to write the file on remote runner.
    """
    a = utils.account_for_user(user)
    assert (prop in a)
    a[prop] = _apply_dm_change(a[prop], key, value)


def get_dm_config_value(user, key, prop="dm_config"):
    """Get specified value in user's DM config.

    *Note*: The value is returned from the in-memory configuration
    tree. This is *not* equal to the configuration on target if
    there is pending changes that has not been deployed using
    \`Deploy dm changes\`."""

    tree = utils.account_for_user(user)[prop]
    items = key.split("/")
    if items[-1].startswith("@"):
        pval = items[-1][1:]
        return tree.find(utils.ns_escape("/".join(items[:-1]))).attrib[pval]
    else:
        return tree.find(utils.ns_escape(key)).text


def deploy_dm_changes(user):
    """Creates/updates dm_config.xml file on the remote runner

    The file is created from the dm_config tree for user's account.
    You can use \`Set dm config value\` to manipulate this tree before
    deploying the changes.

    Sets the dm-url to point to the local file dm_config.xml
    """

    c, a = utils.client_for_user(user), utils.account_for_user(user)
    utils.put_app_file(c,
                       "dm_config.xml",
                       utils.xml_string(a["dm_config"]))
    #logger.debug("Deploy DM Config for user %s. Config:\n%s" %
    #             (user, utils.xml_string(a["dm_config"])))

    client = utils.client_for_user(user)
    app_dir = utils.get_remote_appdir(client)
    if utils.on_windows():
        items = app_dir.split("\\")
        new_app_dir = ""
        for item in items:
            new_app_dir += item + "/"
        app_dir = new_app_dir
    app_file = app_dir + "/" + "dm_config.xml"
    c["dm-url"] = app_file
    if utils.on_ucaas():
        set_app_ini_value(user, "testing/dm_config_file_override",
                          c["dm-url"])
        deploy_app_ini_changes(user)


def reset_dm_config_for_user(user):
    """Take XSP's URL back to use. This means not using defined DM config
    changes."""
    client = utils.client_for_user(user)
    if "dm-url" in client:
        del client["dm-url"]
    fetch_server_data_for_user(user)
    if utils.on_ucaas():
        utils.clear_app_settings(user)
        set_app_ini_value(user, "testing/dm_config_file_override",
                          "")
        deploy_app_ini_changes(user)


def set_app_ini_value(user, key, value):
    """Sets a value in application_setting.ini for given user

    Key must be in path format, e.g. section/item

    *Note*: Sets in-memory config value only. \`Deploy app ini changes\`
    needs to be called to write the file on remote runner.
    """
    c = utils.client_for_user(user)
    c["aut"]["initial_app_ini"][str(key)] = str(value)


def deploy_app_ini_changes(user):
    """Deploys in-memory application_setting.ini to runner

    To configure application settings use \`Set app ini value\`
    before calling this function
    """
    c = utils.client_for_user(user)
    utils.put_app_file(
        utils.client_for_user(user),
        "application_setting.ini",
        create_app_ini(c["aut"]["initial_app_ini"]))


def _fetch_server_data(*users):
    """
    Fetch Xsi directory data, xmpp roster and localstore
    contacts for given users' accounts
    """
    map(fetch_server_data_for_user,
        utils.wildcard_users(users))




def create_xmpp_tool_for_account(account):
    return xmpp_tool.XmppTool(account["xmpp_username"],
                              account["xmpp_password"])


def create_xmpp_tool(user):
    return create_xmpp_tool_for_account(utils.account_for_user(user))


def load_server_data_for_all_accounts(cache_filename):
    """Load server data for all defined accounts either from server or
    from given file if it is newer than 12 hours."""
    if utils.file_newer_than_hours(cache_filename, 12):
        load_account_server_data_from_file(cache_filename)
        return
    for account in ACCOUNTS.values():
        fetch_server_data_for_account(account)
    cache_account_server_data(cache_filename)

'''
def fetch_server_data_for_account(account):
    xsi = create_xsi_tool_for_account(account)
    utils.update_dict(account, xsi.get_directory_data())
    username = account["xsp_username"].split('@')
    client = utils.client_for_user(utils.user_for_account(username[0]))
    ucaas = client.get("ucaas", False)
    kwargs = {"ucaas": ucaas}
    account["dm_config"] = xsi.get_dm_config(**kwargs)
    if not ucaas:
        for x in ["username", "password"]:
            account["xmpp_" + x] = utils.node_value(account["dm_config"],
                                                    "protocols/xmpp/"
                                                    "credentials/%s" % x)
        xmpp = create_xmpp_tool_for_account(account)
        utils.update_dict(account, xmpp.get_xmpp_data())
'''

def fetch_server_data_for_user(user):
    fetch_server_data_for_account(utils.account_for_user(user))


def cache_account_server_data(fname):
    "Write account data to given .json file"
    data = copy.deepcopy(ACCOUNTS)
    for a, val in data.iteritems():
        for k in ["dm_config",
                  "xmpp_roster",
                  "localstore_contacts",
                  "own_vcard"]:
            if k in val and type(val[k]) != str:
                val[k] = utils.xml_string(val[k])
    open(fname, "w").write(json.dumps(data, indent=2))
    return data


def load_account_server_data_from_file(fname):
    "Load account data from given .json file"
    data = json.load(open(fname, "r"))
    for a, val in data.iteritems():
        for k in ["dm_config",
                  "xmpp_roster",
                  "localstore_contacts",
                  "own_vcard"]:
            if k in val:
                val[k] = utils.xml_tree(val[k])

    for k, v in ACCOUNTS.iteritems():
        if k in data.keys():
            v.update(data[k])
    return data


def verify_users_subscribed_to_each_other(*users):

    """Verify that users' accounts have both way XMPP subscriptions to
    each other. Assumes XMPP data has been fetched for each one."""

    def _jid_for_user(user):
        return utils.account_for_user(user)["jid"]

    missing = {}
    for user in users:
        account = utils.account_for_user(user)
        assert "xmpp_roster" in account
        subscribed_contacts = set(
            utils.subscribed_contacts(account["xmpp_roster"]))
        should_have = set([_jid_for_user(u)
                           for u in list(set(users) - set([user]))])
        missing_jids = should_have - subscribed_contacts
        if len(missing_jids) > 0:
            missing[user] = missing_jids

    assert len(missing.keys()) == 0, (
        "\n".join([("User %s has subscription(s) "
                    "missing for %s" % (user, ", ".join(missing_users)))
                   for user, missing_users in missing.iteritems()]))


def get_vcard_data(vcard_xml_tree):
    """Extract base64 encoded values from given VCard data.
    """
    return {key: base64.b64decode(utils.node_value(vcard_xml_tree, path))
            for path, key in (("CATEGORIES/CONF/CALL", "conf-call-number"),
                              ("CATEGORIES/CONF/CHAT", "myroom-uri"))}
