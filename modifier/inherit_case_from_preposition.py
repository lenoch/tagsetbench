from . import Modifier


class inherit_case_from_preposition(Modifier):
    def __init__(self, model):
        model.params['match'] = {'c': '[1-7]'}
        super().__init__(model)  # compile regexes from 'model' as self.match

    def __call__(self, sentence):
        last_case = None

        for i, token in enumerate(sentence.tokens):
            if self.match_attributes(token):
                if token.get('k') == '7':
                    last_case = (i, token['c'])
                elif (last_case and last_case[0] == i - 1 and
                      token.get('k') != '7' and token.get('c') and
                      token.get('c') != last_case[1]):
                    token['c'] = last_case[1]
                    self.mark_modified(token)  # self.silent is honoured
