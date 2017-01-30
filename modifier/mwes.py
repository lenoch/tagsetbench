# TODO: zmodernizovat na Modifier

import json
import re

from . import Modifier
from . import compile_regexes, match_attributes
from . import mwe


# TODO: nesmím tu duplikovat věci, co už mám, takže využít modul 'mwe'
# TODO: ani nevím, jestli modul 'mwe' nějak jinak využívám, takže ho prostě
#       klidně i vložit sem, pokud určitě nebudou jeho služby potřeba mimo
MWE_TYPES = {
    'compound-cardinals': {  # '10 000' as an ideal single token instead of two
        'lc': '\d+ \d.*',
        # řeší to asi mwe.expand_multiword
    },
}


# TODO: kdybych náhodou chtěl rozpadávat nejdřív řadový číslovky a pak čísla
#       složený z více řad číslic, tak vlastně budu rozpadávat už rozpadlý MWE,
#       a to musím poznat, nesmím koukat jen na vnější word, ale taky na to,
#       jestli ten Token už nemá nějaký v sobě (což po rozpadnutí na číslo a
#       tečku bude mít)

class expand(Modifier):
    def __init__(self, model):
        if 'type' in self.model.options:
            self.model.options['match'] = MWE_TYPES[self.model.options['type']]
        super().__init__(model)  # compile regexes from 'model' as self.match

    def __call__(self, sentence):
        for token in sentence.tokens:
            if self.match_attributes(token):
                mwe.expand_token(token)
                self.mark_modified(token)  # self.silent is honoured


def look_inside(sentence, attributes_to_match):
    """
    Don't wrap matched MWEs in <phr/>.
    """
    attributes = prepare_regexes(attributes_to_match)

    for token in sentence.tokens:
        if match_attributes(token, attributes):
            token.use_internal_tokens = True


def prepare_regexes(attributes_to_match):  # for matching
    try:
        # {"lc": "\d \d", tag: "k8xC", …}
        attributes = json.loads(attributes_to_match)
    except json.decoder.JSONDecodeError:
        # TODO: seznam druhů MWE buď jako typ1+typ2 nebo jako JSONovskej seznam
        attributes = MWE_TYPES[attributes_to_match]

    return compile_regexes(attributes)


def compress(sentence, attributes_to_match):
    """
    Replace a MWE with only the surface information.
    """
    # attributes = prepare_regexes(attributes_to_match)

    for token in sentence.tokens:
        token.tokens = []
