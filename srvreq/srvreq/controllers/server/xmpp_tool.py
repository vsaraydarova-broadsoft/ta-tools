from sleekxmpp import ClientXMPP
import sleekxmpp.xmlstream as x
from sleekxmpp.xmlstream import ElementBase
from xml.etree import cElementTree
import utils


class ContactStorage(ElementBase):
    name = 'contact_storage'
    namespace = 'bsft-private-storage'
    plugin_attrib = 'contact_storage'


def _xml_string(stanza):
    return x.tostring(stanza.get_payload()[0])


class _LocalStoreContactsXmppClient(ClientXMPP):
    def __init__(self, jid, password, contact_storage_xml, timestamp):
        ClientXMPP.__init__(self, jid, password)
        self.timestamp = timestamp
        self.contact_storage_xml = contact_storage_xml
        self.add_event_handler("session_start", self._session_start)
        self.register_plugin("xep_0049")
        self["xep_0049"].register(ContactStorage)
        self.register_plugin("xep_0060")
        self.connect()

    def _session_start(self, event):
        contacts_store = cElementTree.fromstring(
            utils.xml_string(self.contact_storage_xml))
        pubsub = cElementTree.fromstring(
            "<last-update>%s</last-update>" % self.timestamp)
        timestamp = cElementTree.fromstring(
            "<timestamp xmlns='bsft-private-storage'>%s</timestamp>" %
            self.timestamp)
        self['xep_0049'].store(timestamp, block=True)
        self['xep_0049'].store(contacts_store[0], block=True)
        node = "contact-storage-update-%s" % self.jid.replace("@", "-")
        item = "contact-storage-date-item-%s" % self.jid.replace("@", "-")
        self['xep_0060'].publish("pubsub.broadsoft.com",
                                 node, item, pubsub)
        self.disconnect()


class _XmppClient(ClientXMPP):
    def __init__(self, jid, password, destroy_contact_storage=False):
        self.destroy_contact_storage = destroy_contact_storage
        ClientXMPP.__init__(self, jid, password)
        self.add_event_handler("session_start", self._session_start)
        self.add_event_handler("roster_update", self._roster_update)
        self.register_plugin("xep_0049")
        self["xep_0049"].register(ContactStorage)
        self.register_plugin("xep_0054")
        self.connect()

    def _session_start(self, event):
        self.send_presence()
        self.get_roster()
        if not self.destroy_contact_storage:
            iq = self['xep_0049'].retrieve("contact_storage", block=True)
            self.localstore_contacts = _xml_string(iq)
        iq = self['xep_0054'].get_vcard(jid=self.jid, block=True)
        self.own_vcard = _xml_string(iq)

    def destroy_localstore_contacts(self):
        self['xep_0049'].store(ContactStorage(), block=True)

    def _roster_update(self, roster):
        self.xmpp_roster = _xml_string(roster)
        if self.destroy_contact_storage:
            self.destroy_localstore_contacts()
        self.disconnect()


class XmppTool():
    def __init__(self, jid, password):
        self.jid = jid
        self.password = password

    def get_xmpp_data(self):
        """Fetches roster and localstore contacts XML for given XMPP account.
        Returns a dict with XML string values."""
        x = _XmppClient(self.jid, self.password)
        x.process(block=True)
        assert all(
            [hasattr(x, a) for a in ["xmpp_roster",
                                     "localstore_contacts",
                                     "own_vcard"]]), (
                "Failed to fetch XMPP data")
        return {
            k: utils.xml_tree(getattr(x, k)) for k in [
                "xmpp_roster",
                "localstore_contacts",
                "own_vcard"]}

    def set_xmpp_data(self, name, **kwargs):
        """Modify localstore contacts XML for given XMPP account.
        """
        assert name == "localstore_contacts", "Not implemented"
        assert all(x in kwargs.keys() for x in ["localstore_contacts",
                                                "timestamp"])
        x = _LocalStoreContactsXmppClient(
            self.jid, self.password,
            kwargs.get("localstore_contacts"), kwargs.get("timestamp"))
        x.process(block=True)

    def destroy_private_storage_contacts(self):
        """Empties XMPP private storage contactlist.
        """
        x = _XmppClient(self.jid, self.password, destroy_contact_storage=True)
        x.process(block=True)
