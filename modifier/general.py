# WISH: přejmenovat na „universal“ (napadlo mě i generic)
from contextlib import suppress

from . import Modifier


class match_delete_replace(Modifier):
    """
    Simple ad-hoc search & replace (& delete). Should contribute to faster
    prototyping.

    MODIFIER
        MATCH
            k=5  # not actually necessary as long as 'm' is unique to k5
                  # (but kY and derived classes (k8) might also carry mC)
            m=N
        SET
            k=2
        DEL
            a     # drop the attribute

    becomes

    params = {
        'match': {
            'k': '5',
            'm': 'N',
        },
        'replace': OrderedDict(
            ('k', '2'),
        ),
        'delete': ['a'],
    }

    TODO: rework this into a doctest (in a suitable location)
    """
    def __init__(self, model):
        super().__init__(model)  # compile regexes from 'model' as self.match
        self.replace = model.params['change']  # SET
        self.delete = model.params['delete']  # DEL

    def __call__(self, sentence):
        for token in sentence.tokens:
            if self.match_attributes(token):
                for attr in self.delete:
                    with suppress(KeyError):
                        del token[attr]

                # token.update(self.replace)
                for attr, value in self.replace.items():
                    if attr == 'tag':
                        # sorry, (vy) ostatní hodnoty…
                        for any_attr, _ in tuple(token.items()):
                            if any_attr not in ('word', 'lemma'):
                                del token[any_attr]
                        token.parse_tag(value)
                    else:
                        token[attr] = value

                self.mark_modified(token)  # self.silent is honoured
