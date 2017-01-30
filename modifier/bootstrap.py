from . import Modifier


# TODO: asi by to už v pohodě šlo s obecným modifikátorem, protože konečně umím
#       předávat dodatečný parametry – takže prostě "implicit/silent" a hotovo

class punctuation(Modifier):
    """
    Explicit, fine-grained, “late-bound” bootstrap.
    """
    def __init__(self, modifier):
        modifier.params['match'] = {
            'k': '\?',
            'word': """[-,.():?"!;\'/]|...""",
        }
        super().__init__(modifier)
        self.explicit = modifier.params.get('explicit', 'no').lower() in (
            'yes', 'true')
        ####self.untagged_sign = modifier.params.get('', 'no').lower() in (
        ####    'yes', 'true')
        # remove the hacked-in MATCH dictionary from the modifier name
        mod = self.name.split(';')
        self.name = ';'.join(mod[:mod.index('MATCH')])

    def __call__(self, sentence):
        for token in sentence.tokens:
            if self.match_attributes(token):
                token['k'] = 'I'
                # NOTE: bootstraping leaves no mark unless you make a wish
                if self.explicit:
                    token['z'] = 'X'  # nasrat na zX; stačí <phr/>
                    token.set_modified_by(self.name)
                # TODO: používat přímo Modification.name?


class cardinal_number(Modifier):
    """
    Explicit, fine-grained, “late-bound” bootstrap.
    """
    def __init__(self, modifier):
        modifier.params['match'] = {
            'k': '\?',
            'word': '[0-9 ]+',
        }
        super().__init__(modifier)
        self.explicit = modifier.params.get('explicit', 'no').lower() in (
            'yes', 'true')
        # remove the hacked-in MATCH dictionary from the modifier name
        mod = self.name.split(';')
        self.name = ';'.join(mod[:mod.index('MATCH')])

    def __call__(self, sentence):
        for token in sentence.tokens:
            if self.match_attributes(token):
                token['k'] = '4'
                token['x'] = 'C'  # základní číslovka
                if self.explicit:
                    token['z'] = 'X'  # tohle jde v pohodě zahodit…
                    token.set_modified_by(self.name)


# elif line == '%':
#     tag = 'k1gNzX'  # lemma: “procento” (neutral gender)
# else:
#     tag = 'k1zX'
