import io
import collections
from lxml import etree as et


def xml_string(tree):
    if isinstance(tree, et._ElementTree):
        return et.tostring(tree.getroot(),
                           encoding="UTF-8",
                           xml_declaration=True,
                           pretty_print=True)
    return tree


def xml_tree(s):
    return et.parse(io.BytesIO(str(s)))


def value_to_str(x):
    if isinstance(x, bool):
        return "true" if x else "false"
    return x


def ns_escape(path):
    return "/".join(map(lambda x: "{*}%s" % x, path.split("/")))


def is_truthy(x):
    return x is True or x.lower() in ['true', '1', 'yes']


def str_to_bool(strbool):
    return is_truthy(strbool)


def bool_to_str(b):
    return "true" if b else "false"


def node_value(elem, path):
    e = elem.find(ns_escape(path))
    return e.text if e is not None else None


def node_values(elem, path):
    return map(lambda x: x.text, elem.findall(ns_escape(path)))


def localname(elem):
    return et.QName(elem).localname


def node_list(elem):
    """Enumberate children and return dictionary {tag:value, }
    """
    def _type(value):
        if value is None or \
           value.lower() not in ['true', 'false']:
            return value
        return is_truthy(value)

    return dict([(localname(x), _type(x.text)) for x in list(elem)])


def element(name):
    return et.Element(name)


def sub_element(root, tag, value):
    et.SubElement(root, tag).text = value_to_str(value)


def update_dict(d, u):
    """
    Recursively update dictionary d with dictionary u
    """
    for k, v in u.iteritems():
        if isinstance(v, collections.Mapping):
            r = update_dict(d.get(k, {}), v)
            d[k] = r
        else:
            d[k] = u[k]
    return d