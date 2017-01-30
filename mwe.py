# from copy import deepcopy
import re

from symbols import Token

ORDINAL_NUMBER = re.compile('(\d+)\.')


# TODO: tohle nepoužívám (snad ani v testech), tak nějak rozsekat (využít
#       v modification.handle_mwes) a pohřbít
def handle_mwes(tokens, args):
    """
    NOTE: většinu MWE mám v úsporné formě, takže by default se nechají být
    TODO: rozšiřovat se budou jenom vybraný druhy MWE, např. řadový číslovky,
          čísla s mezerama/desetinama, zkratky (s tečkou) a jména (bohužel
          nemám odlišená cizí)
    """
    to_compress = args['compress']
    to_expand = args['expand']

    for xml_tag, token in tokens:
        if xml_tag:
            for line_number, line in xml_tag.original_lines:
                yield line
        else:
            mwe_type = guess_type(token)
            if mwe_type and mwe_type in to_compress:
                yield from compress_token(token, mwe_type).plain_vertical()
            elif mwe_type and mwe_type in to_expand:
                yield from expand_token(token, mwe_type).plain_vertical()
            else:
                for line_number, line in token.original_lines:
                    yield line


def guess_type(token):
    if token['word'].endswith('.'):
        ordinal = ORDINAL_NUMBER.match(token['word'])
        if ordinal:
            return 'ordinal'
        elif token.get('z') == 'A':
            return 'abbreviation'
    elif ' ' in token['word']:
        return 'multiword'


def expand_tokens(tokens, output_file):
    """
    TODO: převeď jednořádkový MWE na <phr/>
    TODO: jednoduše převeď <phr/> s w=, l=, t= a <g/> na jednořádkovej zápis

          v jednom řádku je word, co může obsahovat mezery, lemma stejně tak
          (a nejen mezery, i tečky a další věci, co tokenizer dává samostatně),
          a nakonec společnej tag – anebo možná i tolik tagů, kolik je
          „hloupejch“ tokenů – no a to vše oddělený tabulátorama

          takže tady budu re-tokenizovat (rekonstruovat, jak to původně hloupě
          bylo) a dávat značky – buď jednu a tu samou, anebo (v případě čísel)
          takovou, co odpovídá povaze tokenu (díky jednoduchým regexům)
    """
    pass


# TODO: tuhle funkci už určitě používám v Modifier.bootstrap().
def compress_token(token):
    """
    Return regular tokens unchanged. Return <phr/> as a single line (with tabs
    to delimit columns/“attributes”, and squashing <g/>).
    """
    pass


def expand_token(token, mwe_type=None, force=False):
    """
    Return regular tokens unchanged. Return a token containing heterogenous
    content (punctuation, spaces) as <phr/> with each token on a line of its
    own, delimited by <g/> where there was no whitespace.
    """
    # TODO: test zatím nepředává mwe_type
    if mwe_type is None:
        mwe_type = guess_type(token)

    if mwe_type == 'ordinal':
        ordinal = ORDINAL_NUMBER.match(token['word'])
        if ordinal:
            return expand_ordinal(token, ordinal)

    elif mwe_type == 'abbreviation':
        return expand_abbrev(token)

    elif mwe_type == 'multiword':
        multiword = expand_multiword(token)
        if multiword:
            return multiword

    if force:
        token.tokens = [Token.from_Token(token)]
        return token

    return token


def expand_abbrev(token):
    abbrev = Token.from_Token(token, word=token['word'][:-1])
    abbrev.trailing_whitespace = False
    token.tokens = [abbrev, Token(word='.', lemma='.', k='I', x='.',
                                  final=True, begin=token.begin)]
    return token


def expand_ordinal(token, ordinal):
    number = Token(word=ordinal.group(1), lemma='#' * len(ordinal.group(1)),
                   k='4', trailing_whitespace=False)

    token.tokens = [number, Token(word='.', lemma='.', k='I', x='.',
                                  final=True)]
    # TODO: testovat ještě zpětně sestavenej token, jestli se projevuje
    #       trailing_whitespace a final
    for t in token.tokens:
        t.begin = 0
    return token


def expand_multiword(token):
    # kdyby tam byly nějaký apostrofy a tak… tak samozřejmě s těma taky počítat
    # a chytře tokenizovat
    # TODO: tokenizovat se dá zase s regexama, vždyť to znám…

    # TODO: pak teda nějak nahradit chytřejším tokenizátorem
    words = token['word'].split()
    lemmata = token['lemma'].split()
    lemma = iter(lemmata)
    if len(words) == len(lemmata):
        # TODO: zase, prostě nejdřív ten původní token naklonovat, ať zůstanou
        #       značky (tady už s nima nic vymejšlet nebudu, nejsem tagger)
        token.tokens = [Token.from_Token(token, word=word, lemma=next(lemma))
                        for word in words]
        return token
