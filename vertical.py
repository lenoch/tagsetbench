import sys

from log import log
from symbols import Token
from xml_tag import XmlTag


# TODO: @custom_repr
class Sentence:
    def __init__(self, tokens, opening_tag, closing_tag):
        self.tokens = tokens
        self.opening_tag = opening_tag
        self.closing_tag = closing_tag

    def lines(self):
        yield self.opening_tag
        for token in self.tokens:
            yield from token.lines()
        yield self.closing_tag

    def __repr__(self):
        return "Sentence({!r})".format(self.tokens)

    def check_match(self, other):
        """
        Do some stupid checks (well, not so stupid, this actually matches
        my intention to have a 'strict checking' mode which ensures only
        comparable corpora are processed).
        """
        sentence_number = self.opening_tag['number']
        if sentence_number != other.opening_tag['number']:
            raise ValueError('Nesedí čísla vět mezi vzorovým a označkovaným '
                             'korpusem: {} vs. {}'.format(
                                sentence_number, other.opening_tag['number']))

        # TODO: vyprdnout se na tohle předpočítávání a prostě použít len(),
        #       ono stejně už asi je předpočítaný (anebo jméno: token_count)
        if len(self.tokens) != len(other.tokens):
            compared_tokens = iter(other.tokens)
            for reference_token in self.tokens:
                compared_token = next(compared_tokens)
                print(reference_token, compared_token)

            raise ValueError('Nesedí počet tokenů mezi vzorovým a označkovaným'
                             ' korpusem: {} vs. {} ve větě {}'.format(
                                 len(self.tokens), len(other.tokens),
                                 sentence_number))


def read_sentences(lines=sys.stdin, token_parser=None):
    tokens = []
    opening_tag = None

    for xml_tag, token in read_vertical(lines, token_parser):
        if xml_tag:
            if xml_tag.name in ('s', 'head'):
                if xml_tag.opening:
                    opening_tag = xml_tag
                else:  # closing tag
                    yield Sentence(tokens, opening_tag, xml_tag)
                    opening_tag = None
                tokens = []

        elif opening_tag:  # open sentence, expect tokens
            tokens.append(token)


def read_vertical(lines=sys.stdin, token_parser=None, token_number=0):
    """
    The function cannot straightforwardly be split into a MWE-handling part
    without also taking care of <g/>s as these can be embedded in MWEs.

    While the function automatically adds missing </phr> to MWEs and closes
    MWEs on </s>, it does not automatically yield </s> if missing at the end of
    input.
    """
    open_mwe = None
    # always points to the token (even as a part of open_mwe) waiting for its
    # <g/> or other type of termination (other token, sentence/MWE boundary, …)
    open_token = None

    for xml_tag, new_token in parse_lines(lines, token_parser):
        if xml_tag:
            if xml_tag.name == 'phr':  # MWE
                if xml_tag.opening:
                    if open_mwe:
                        open_token = _close_mwe(open_mwe)
                    if open_token:
                        token_number = yield (None, open_token)
                        open_token = None
                    xml_tag.token_number = token_number or 0
                    open_mwe = Token.from_XmlTag(xml_tag)
                elif open_mwe:  # </phr>
                    open_token = _close_mwe(open_mwe,
                                            last_lines=xml_tag.original_lines)
                    open_mwe = None
                else:
                    log.warning('stray </phr>!')
            elif xml_tag.name == 'g':  # po předchozím tokenu nemá bejt mezera
                if open_token:
                    open_token.trailing_whitespace = False
                    open_token.original_lines.extend(xml_tag.original_lines)

                if open_mwe:
                    open_mwe.original_lines.extend(xml_tag.original_lines)
                elif open_token:
                    token_number = yield (None, open_token)
                    open_token = None
                else:
                    log.warning('stray <g/>!')
            else:  # other XML tag
                if open_mwe:
                    if xml_tag.name not in ('s', 'head'):
                        log.warning('%s inside <phr>, closing',
                                    (xml_tag.original_lines,))
                    open_token = _close_mwe(open_mwe)
                    open_mwe = None
                if open_token:
                    token_number = yield (None, open_token)
                    open_token = None

                token_number = yield (xml_tag, None)
        else:
            # deal with the open one first (there was no <g/>)
            if not open_mwe and open_token:
                token_number = yield (None, open_token)
                open_token = None

            new_token.begin = token_number or 0
            open_token = new_token
            if open_mwe:
                open_mwe.append_internal_token(open_token)

    if open_mwe:
        open_token = _close_mwe(open_mwe)
    if open_token:
        yield (None, open_token)


def _close_mwe(mwe, last_lines=None):
    if mwe.tokens:
        mwe.tokens[-1].final = True
    if not mwe.get('word'):
        mwe['word'] = mwe.join_internal_tokens()
    if last_lines:
        # The model allows for multiple lines (to accomodate well for MWEs, but
        # here, it’s (always) only </phr>.
        mwe.original_lines.extend(last_lines)
    return mwe


def parse_token(line):
    word, *attrs, tag = line.split('\t')
    lemma = attrs[0] if attrs else ''
    return {'word': word, 'lemma': lemma, 'tag': tag}


def parse_lines(lines=sys.stdin, token_parser=None):
    if token_parser is None:
        token_parser = parse_token

    for line_number, line in enumerate(lines, 1):
        line = line.strip()
        if not line:
            continue
        elif line.startswith('<') and line.endswith('>'):
            yield XmlTag.parse(line, line_number), None
        else:
            yield None, Token.from_line(line, token_parser, line_number)


def parse_token_with_two_tags(line):
    word, lemma, *tags = line.split('\t')
    original_tag = tags.pop(0)
    new_tag = tags[0] if tags else original_tag  # was: None
    return {'word': word, 'lemma': lemma, 'tag': original_tag,
            'new_tag': new_tag}


# unused

def read_logical_tokens_numbered(lines=sys.stdin, token_parser=None):
    token_number = 0
    parser = read_vertical(lines, token_parser, token_number=token_number)

    # NOTE: StopIteration is simply passed through.
    xml_tag, token = parser.send(None)
    while True:
        yield xml_tag, token

        if xml_tag:
            if xml_tag.name in ('s', 'head'):
                token_number = 0
        else:
            token_number += 1

        xml_tag, token = parser.send(token_number)
