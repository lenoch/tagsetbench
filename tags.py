from collections import defaultdict
from itertools import zip_longest

ATTRS = ['word', 'lemma'] + list('kegvncpamdxytzw~')
ATTR_MAP = {attr: attr_id for (attr_id, attr) in enumerate(ATTRS)}
ATTR_IDS = list(range(len(ATTRS)))


def extract_attributes_from_tag(tag):
    # TODO: also return tag in .ambiguous so matching on tag works
    # MAYBE: support k1c14 (multiple-valued attributes in a short form)
    if ',' in tag:
        tags = tag.split(',')
        if '' not in tags:
            return put_ambiguous_attrs_aside(tags)
    if len(tag) % 2 != 0:
        raise ValueError('Malformed tag "{}"'.format(tag))
    return list(grouper(tag, 2)), []


def put_ambiguous_attrs_aside(tags):
    # MAYBE: support ambiguous tags of uneven length: c1,c2d1
    all_values = defaultdict(set)
    parsed_tags = []

    for tag in tags:
        if len(tag) % 2 != 0:
            raise ValueError('Malformed tag "{}"'.format(tag))
        attrs = list(grouper(tag, 2)) + [('tag', tag)]
        for attr, value in attrs:
            all_values[attr].add(value)
        parsed_tags.append(attrs)

    unambiguous = {attr: values.pop() for (attr, values) in all_values.items()
                   if len(values) == 1}
    ambiguous = []
    for attrs in parsed_tags:
        ambiguous_group = {attr: value for (attr, value) in attrs
                           if attr not in unambiguous}
        if ambiguous_group:
            ambiguous.append(ambiguous_group)
    return unambiguous, ambiguous


# copied from oVirt/VDSM, which in turn used
# http://docs.python.org/2.6/library/itertools.html?highlight=grouper#recipes
def grouper(iterable, n, fillvalue=None):
    "Collect data into fixed-length chunks or blocks"
    # grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx
    args = [iter(iterable)] * n
    return zip_longest(fillvalue=fillvalue, *args)
