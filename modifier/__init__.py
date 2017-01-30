import re

# NOTE: to je kvůli rftagger_preprocess, aby mohl 'from . import rftagger'
import mwe
import rftagger


class Modifier:
    def __init__(self, model=None, match=None, name=None):
        self.model = model  # a concrete instance of the modifier, with params
        self.match = match or {}
        self.name = name or ''  # WISH: bez modelu brát z názvu třídy

        if self.model:
            params = self.model.params
            self.match.update(params['match'])  # WISH: match0, match-1, …

            alias = params.get('alias')  # marker/fingerprint?
            # takhle dokážu předat "", aby to třeba ztichlo
            if alias is not None:
                self.name = alias
            else:
                self.name = ';'.join(part.strip() for part
                                     in self.model.encode()
                                     if 'MODIFIER' not in part)

            # NOTE: na tichej bootstrap („implicitní“ modifikátory)
            # LEAVE NO TRACE
            self.silent = params.get('silent', 'no') in ('yes', 'true', '')

        compile_regexes(self.match)
        self.tokens_matched = 0
        self.tokens_marked_modified = 0  # match_attributes might be too basic
        self.tokens_modified = 0

    def match_attributes(self, token):
        if match_attributes(token, self.match):
            self.tokens_matched += 1
            return True

    def mark_modified(self, token):
        self.tokens_modified += 1
        if not self.silent:
            token.set_modified_by(self.name)
            self.tokens_marked_modified += 1


# WISH: merge into Modifier (as a method) once all are converted
def compile_regexes(attributes):
    for attr, regex in tuple(attributes.items()):
        attributes[attr] = re.compile(regex)

    return attributes


# TODO: i tohle dát do Tokenu? (zatím jsem to dal jako metodu Modifieru)
def match_attributes(token, attributes):
    for attr, regex in attributes.items():
        if attr not in token or not regex.fullmatch(token[attr]):
            return False

    return True
