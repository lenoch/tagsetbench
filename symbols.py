# from collections import namedtuple
from itertools import chain
import re

# import edge
from log import log, DEBUG
from shlex import escape, shlex  # shlex je teď můj (a mám escape místo quote)
from tags import ATTRS, ATTR_IDS, ATTR_MAP, extract_attributes_from_tag
from xml_tag import XmlTag

# TODO: doplnit tokens?
ALL_META = ('line', 'edge', 'optional', 'begin', 'length', 'head', 'dep',
            'trailing_whitespace', 'phrase', 'ambiguous')


# TODO: víceúrovňový lookup: collections.ChainMap


class Attr:
    def __init__(self, value, attr_id, position=None):
        self.value = value
        self.attr_id = attr_id
        # pozice v attrs_nonempty, aby se nemuselo hledat
        self.position = position
        # TODO: previous (a next)?

    @property
    def attr(self):  # TODO: name
        return ATTRS[self.attr_id]


class Attrs:
    """
    Náhrada za tu šílenost v predict()! Ještě větší šílenost :-)

    Při porovnávání v původním Symbolu, který je postaven nad slovníkem, se
    nějak iteruje přes první slovník a nejspíš se musí hashovat, aby se dalo
    přistoupit ke každému prvku v druhém slovníku.

    Chci to udělat jinak: iterovat jistě v lineárním čase a přistupovat
    k odpovídajícím prvkům v konstantním čase.

    Na to je potřeba zabrat víc místa a prostě mít v každém Symbolu seznam
    prvků s pevným pořadím.

    V jednom bude třeba:
        self.attrs_fixed = [
            (0, '2'),  # k
            None,      # e
            (2, 'F'),  # g
            (3, 'S'),  # n
            (4, '1'),  # c
            None,      # p
            …
        ]

        self.attrs_nonempty = [
            (3, 'S'),  # n
            (0, '2'),  # k
            (4, '1'),  # c
            (2, 'F'),  # g
        ]

    V druhém podobně. Iterovat se bude přes ten druhý, neprázdné prvky se budou
    sdílet. Kvůli konstatnímu přístupu ke druhým atributům má každý prvek
    v sobě ještě attr_id.

    Zabraná paměť: tuple + attr_id + value pro každý atribut, fixní seznam
    a proměnlivý seznam za každý neprázdný atribut.

    Operace porovnání:
    Časová složitost je lineární vzhledem k počtu neprázdných atributů. Bohužel
    nevím, jestli náhodou neřešit i neprázdné atributy na druhé straně. To chce
    use-case. Ale když mám dvojici (attr_id, value), tak mi stačí
        other.attrs_fixed[attr_id] a mám odpovídající dvojici – v konst. čase
    Pokud se porovnávání používá často, tak si ušetřím hashování, které sice
    má být rychlé, ale nějakou cenu určitě má.

    Takže jak přidám/změním hodnotu?
        1) Přeložím si název atributu na jeho číslo.
        2) Podívám se na odpovídající pozici v attrs_fixed.
        3) Když tam už něco je, prostě aktualizuju hodnotu.
        4) Když tam nic není, vložím tam novou dvojici a přesně tu samou
           dvojici _přidám_ na konec attrs_nonempty.

    Co kopírování?
        To chci mít copy-on-write, takže seznamy zkopíruju až při __setitem__
        (jedinkrát to bude stačit, takže to chce možná ještě nějaký příznak, že
         už to je „moje“).

    A inicializace?
        Ta zahrnuje asi i kopírování, to udělat stejně. Příznak „shared“.

    Co atributy navíc?
        Možná s jinými tagsety by bylo potřeba, ale pro ty se dá udělat vlastní
        Symbol a optimalizovat ho jinak.

    Co meta?
        Nejlepší by bylo Symbol rozdělit na tři podle mého jiného pokusu, ale
        to nejde udělat najednou, nejdřív jsou potřeba testy, jak jsem je tam
        začal. Jinak holt meta musí zůstat, jak je.

    Konečná:
        Atributy se dají ukládat i jako bitová maska, pokud se zafixují. Kvůli
        nejednoznačnosti by jich prostě bylo víc. Ale porovnávání jak z praku.
    """

    def __init__(self, other=None, ambiguous=[], **kwargs):
        if other is not None:
            self.attrs_fixed = other.attrs_fixed
            # TODO: (automaticky se řadící) spojovaný seznam? (asi oboustranně
            #       kvůli mazání)
            self.attrs_nonempty = other.attrs_nonempty
            self.ambiguous = other.ambiguous  # TODO: set() kvůli porovnávání?
            # TODO: tohle ať si udělá Token a ostatní po svém (až odstraním
            #       Symbol)
            self.extra = dict(other.extra)
            self.shared_attrs = True
            other.shared_attrs = True  # už by se neměl modifikovat, ale co
        else:
            self.attrs_fixed = [None for _ in range(len(ATTRS))]
            self.attrs_nonempty = []  # tuples of (attr_id, value)
            self.ambiguous = ambiguous
            self.extra = {}  # cokoli dalšího z vertikálu
            self.shared_attrs = False

        for attr, value in kwargs.items():
            self[attr] = value

    def __contains__(self, key):
        attr_id = ATTR_MAP.get(key)
        if attr_id is not None:
            return self.attrs_fixed[attr_id] is not None
        else:
            return key in self.extra

    def __getitem__(self, key):
        attr_id = ATTR_MAP.get(key)
        if attr_id is not None:
            pair = self.attrs_fixed[attr_id]
            if pair is None:
                raise KeyError(key)
            else:
                return pair.value
        else:
            return self.extra[key]

    def __setitem__(self, key, value):
        if self.shared_attrs:
            self.attrs_fixed = list(self.attrs_fixed)
            self.attrs_nonempty = list(self.attrs_nonempty)
            self.shared_attrs = False

        attr_id = ATTR_MAP.get(key)
        if attr_id is not None:
            old_pair = self.attrs_fixed[attr_id]
            new_position = len(self.attrs_nonempty) if old_pair is None else (
                old_pair.position)
            pair = Attr(value, attr_id, new_position)
            self.attrs_fixed[attr_id] = pair
            if old_pair is None:
                self.attrs_nonempty.append(pair)
            else:
                # pair.value = value  # TODO: blbost, a testovat to!
                self.attrs_nonempty[new_position] = pair
        else:
            self.extra[key] = value

    def update(self, attrs):
        iterable = attrs if isinstance(attrs, list) else attrs.items()
        for attr, value in iterable:
            self[attr] = value

    def pop(self, key, default=None):
        if self.shared_attrs:
            self.attrs_fixed = list(self.attrs_fixed)
            self.attrs_nonempty = list(self.attrs_nonempty)
            self.shared_attrs = False

        attr_id = ATTR_MAP.get(key)
        if attr_id is not None:
            pair = self.attrs_fixed[attr_id]
            self.attrs_fixed[attr_id] = None
            if not pair:
                return default

            self.attrs_nonempty.pop(pair.position)
            # TODO: přečíslovávat až od pozice
            for position, attr_pair in enumerate(self.attrs_nonempty):
                attr_pair.position = position
            return pair.value
        else:
            return self.extra.pop(key, default)

    __delitem__ = pop

    def items(self):
        for attr_pair in self.attrs_nonempty:
            yield attr_pair.attr, attr_pair.value
        for attr, value in self.extra.items():
            yield attr, value

    def get(self, key, default=None):
        attr_id = ATTR_MAP.get(key)
        if attr_id is not None:
            pair = self.attrs_fixed[attr_id]
            if pair is None:
                return default
            else:
                return pair.value
        else:
            return self.extra.get(key, default)

    def __eq__(self, other):
        if len(self.attrs_nonempty) != len(other.attrs_nonempty):
            return False
        for attr_pair in self.attrs_nonempty:
            other_pair = other.attrs_fixed[attr_pair.attr_id]
            if other_pair is None or attr_pair.value != other_pair.value:
                return False
        return True

    def __ne__(self, other):
        return not self.__eq__(other)

    def __le__(self, other):
        other_pairs = other.attrs_fixed
        for attr_pair in self.attrs_nonempty:
            other_pair = other_pairs[attr_pair.attr_id]
            if other_pair is None:
                return False
            elif attr_pair.value != other_pair.value:
                return False  # žádné regexy
        return True

    def __format__(self, format_spec=''):
        ftr = attr_contains_value if 'd' in format_spec else None
        ambiguous = ['/ {}'.format(attrs) for attrs in self.ambiguous]
        attrs = (attr.attr if attr.value is True else attr.attr + '=' +
                 escape(attr.value) for attr in filter(ftr, self.attrs_fixed))
        ret = ' '.join(chain.from_iterable((attrs, ambiguous)))
        if 'd' in format_spec:
            return ret.replace('"', '\"')
        else:
            return ret

    def __str__(self):
        return format(self)

    def __repr__(self):
        return 'Attrs(' + escape(self) + ')'

    def __iter__(self):
        for attr_pair in self.attrs_nonempty:
            yield attr_pair.attr

    # TODO: patří to až do Tokenu, ale teď to potřebuje Symbol (pak přesunout)
    # TODO: nešlo by to teda volat ze Symbolu jako Token.parse(self, tag)?
    def parse_tag(self, tag):
        attrs, ambiguous_groups = extract_attributes_from_tag(tag)
        self.update(attrs)
        self.ambiguous = []
        for attrs in ambiguous_groups:
            ambiguous = Attrs()
            ambiguous.update(attrs)
            self.ambiguous.append(ambiguous)

    # TODO: tohle asi taky, že jo?
    @property
    def tag(self):
        if self.ambiguous:
            tags = []
            for ambiguous_group in self.ambiguous:
                attrs = Attrs(self)
                attrs.ambiguous = []
                attrs.update(ambiguous_group)
                tags.append(attrs.tag)
            return ','.join(tags)
        return ''.join(attr.attr + attr.value for attr in self.attrs_fixed[2:]
                       if attr and attr.value is not True)


class Symbol(Attrs):
    def __init__(self, symbol=None, line=None, edge=None, optional=None,
                 begin=None, length=None, head=None, dep=None,
                 trailing_whitespace=True, phrase=None, tag=None,
                 ambiguous=[], **kwargs):
        if symbol is not None:
            if isinstance(symbol, str):
                symbols = read_rule(symbol, rule_symbol_type=type(self))
                try:
                    symbol = next(symbols)
                except StopIteration:
                    raise ValueError('No symbol passed: "' + symbol + '"')
                # '•' neprojde
                more_symbols = list(symbols)
                if more_symbols:
                    # TODO: taky ValueError?
                    log.warning('Extra symbols passed, ignoring them: %s',
                                ' '.join(str(t) for t in more_symbols))
            super().__init__(symbol)
            self.phrase = symbol.phrase
            self.line = symbol.line
            self.edge = symbol.edge
            self.optional = symbol.optional
            self.begin = symbol.begin
            self.length = symbol.length
            self.head = symbol.head
            self.dep = symbol.dep
            self.trailing_whitespace = symbol.trailing_whitespace
        else:
            super().__init__(ambiguous=ambiguous, **kwargs)
            self.phrase = phrase
            self.line = line
            # self.extra = extra  # další sloupce z vertikálu (třeba závislost)
            self.edge = edge
            self.optional = optional
            self.begin = begin  # pořadové číslo
            self.length = length
            self.head = head
            self.dep = dep
            self.trailing_whitespace = trailing_whitespace
        if tag:
            self.parse_tag(tag)

    @property
    def end(self):
        return self.begin + self.length

    def __eq__(self, other):
        # na tak horkém místě nemám na podobné otázky čas
        # if isinstance(other, str):
        #     return False
        if self.begin != other.begin or self.length != other.length:
            return False
        else:
            # tam porovnávám _seznamy_ nejednoznačných skupin atributů
            return super().__eq__(other) and self.ambiguous == other.ambiguous

    def __ne__(self, other):
        return not self.__eq__(other)

    # __le__ / __ge__ ?
    def match_nonterminal(self, closed_left):
        # self taky není terminál (token), jen symbol hrany (pravidla)
        # TODO: a hlavně se podívat, jestli se to třeba nepodobá match_terminal
        for attr, value in self.items():
            # log.debug('             trying to match %s=%s in %s', attr,
            #           value, closed_left)
            if value is True:
                pass
            elif attr not in closed_left:
                if log.isEnabledFor(DEBUG):
                    log.debug('not present  %s in %s', attr, closed_left)
            elif closed_left[attr] is True:
                if log.isEnabledFor(DEBUG):
                    log.debug('unset value  %s=%s', attr, closed_left[attr])
            elif not re.fullmatch(value, closed_left[attr]):
                return False
        return True

    # TODO: support groups of self.ambiguous attributes
    def match_terminal(self, token):
        if self.phrase:
            return False

        # log.debug("try match    %s = %s", self, token)
        for attr, expected_value in self.items():
            if expected_value is True:
                continue
            elif attr not in token:
                if log.isEnabledFor(DEBUG):
                    log.debug('no attr      %s has no %s=%s', token, attr,
                              expected_value)
                return False
            elif token[attr] is True:
                # log.debug("null attr    %s (expected: %s)", attr,
                #           expected_value)
                raise AssertionError('Attribute %s is True in %s, not %s' % (
                    attr, token, expected_value))
            if not re.fullmatch(expected_value, token[attr]):
                # log.debug("mismatch     %s=%s (expected: %s)", attr,
                #           token[attr], expected_value)
                return False
        if log.isEnabledFor(DEBUG):
            log.debug("match        %s = %s", token, self)
        return True

    def __format__(self, format_spec=''):  # 's' for (equal) span
        equal_span = 's' in format_spec

        phrase_head = self.phrase
        phrase_head = [phrase_head] if phrase_head else []
        is_head = ['head'] if self.head else []
        dependency = ['dep=' + escape(self.dep)] if self.dep else []
        attrs = super().__format__(format_spec)
        attrs = [attrs] if attrs else []
        auxiliary = []
        for attr, value in sorted(self.extra.items()):
            if value is True:
                auxiliary.append(attr)
            elif value is not None:
                auxiliary.append(attr + '=' + escape(value))
        span = ['%s–%s' % (self.begin, self.end)] if (
            self.length is not None and (self.length or equal_span)) else []
        optional = ')?' if self.optional else ')'
        return ('(' + ' '.join(attr_value for attr_value in chain(
            phrase_head, is_head, attrs, auxiliary, dependency,
            span)) + optional)

    def __str__(self):
        return format(self, 's')

    def __repr__(self):
        return 'Symbol(' + escape(self) + ')'

    def update(self, symbol=None, **kwargs):
        if symbol is not None:
            super().update(symbol)
        if isinstance(symbol, Symbol):
            for meta in ALL_META:
                self.__dict__[meta] = symbol.__dict__[meta]
        for attr in dict(kwargs):
            if attr in ALL_META:
                self.__dict__[attr] = kwargs
                kwargs.pop(attr, None)

    def update_from_nonterminal(self, closed_left):
        for attr, value in closed_left.items():
            if value is not True:
                self[attr] = value
        for meta in ALL_META:
            self.__dict__[meta] = closed_left.__dict__[meta]

    def _update_from_nonterminal(self, closed_left):
        for attr, value in closed_left.items():
            if value is True:
                if log.isEnabledFor(DEBUG):
                    log.debug('unset value  %s', attr)
                continue  # asi by se nemělo kopírovat; nejspíš nemělo
            # TODO: logovat, jen když je zapnuté --edges
            old_value = self.get(attr)
            if log.isEnabledFor(DEBUG) and old_value in (None, True):
                log.debug('move         %s=%s → %s', attr, value, self)
            elif self[attr] != value:
                log.warning('update       %s=%s → %s (from %s)', attr, value,
                            self, old_value)
            self[attr] = value

    def parsed_vertical(self):
        # TODO: předělat na generátor
        glue = '' if self.trailing_whitespace else '\n<g/>'
        return '{}\t{}\t{}\t{}{}'.format(
            self.get('word', ''), self.get('lemma', ''), self.tag,
            self.begin, glue)

    def serialize(self):
        # TODO: dodělat u nástupnických tříd
        if hasattr(self.edge, 'id'):
            edge = self.edge.id
        else:
            edge = None if self.edge is None else str(self.edge)
        return dict(
            word=self.get('word'),
            lemma=self.get('lemma'),
            phrase=self.phrase,
            edge=edge,
            begin=self.begin,
            length=self.length,
            str=str(self),
        )


class Token(Attrs):
    def __init__(self, begin=None, tokens=None, original_lines=None,
                 trailing_whitespace=True, tag=None, final=None,
                 modified_by=None, new_tag=None, use_internal_tokens=None,
                 print_original_tag=False, **kwargs):
        super().__init__(**kwargs)  # včetně word, lemma
        if tag:
            self.parse_tag(tag)  # rozparsované atributy
        self.begin = begin  # číslo tokenu ve větě (seq)
        self.length = 1
        # jestli se následující token lepí bez mezery (viz ještě self.final)
        self.trailing_whitespace = trailing_whitespace
        self.tokens = tokens  # parts of a MWE (internal tokens or subtokens)
        self.original_lines = original_lines
        self.original_tag = tag
        self.final = final  # spoluovlivňuje, jestli se má vypisovat <g/>

        # tagsetbench evaluation
        self.print_original_tag = print_original_tag  # in <phr/>
        self.modified_by = modified_by or []
        self.new_tag = new_tag
        if self.new_tag:
            self.new_tag_fake_token = Token(tag=new_tag)  # parse the 'new' tag
        else:
            self.new_tag_fake_token = None
        self.use_internal_tokens = use_internal_tokens  # annotate, …

    def __contains__(self, key):
        if key in ('lc', 'tag'):
            return True
        else:
            return super().__contains__(key)

    def __getitem__(self, key):
        if key == 'lc':
            return self['word'].lower()
        if key == 'tag':
            return self.tag
        else:
            return super().__getitem__(key)

    def __format__(self, format_spec=''):
        attrs = super().__format__(format_spec)
        attrs = [attrs] if attrs else []
        glue = [] if self.trailing_whitespace else ['NO_TRAILING_SPACE']
        span = ['{}–{}'.format(self.begin, self.begin + 1)]
        return '(' + ' '.join(attr_value for attr_value in chain(
            attrs, glue, span)) + ')'

    def __repr__(self):
        return 'Token(' + escape(self) + ')'

    # TODO: prostě jenom vertical… (pak jen doplním self.begin a self.parent)
    def plain_vertical(self, expanded=True, original_tag=False):
        tag = self.original_tag if original_tag else self.clean_tag
        if self.tokens and expanded:
            xml_tag = XmlTag(name='phr', attributes=[
                ('w', self['word'] or ''), ('l', self['lemma'] or ''),
                ('t', tag)])
            if self.print_original_tag:
                xml_tag.attributes.append(('original_tag', self.original_tag))
            xml_tag.attributes.extend(('modified_by', modification_name) for
                                      modification_name in self.modified_by)
            if self.new_tag and self.new_tag != self.original_tag:
                xml_tag.attributes.append(('new_tag', self.new_tag))
            if self.use_internal_tokens:
                xml_tag.attributes.append(('use_internal_tokens', 'true'))
            yield str(xml_tag)
            for internal_token in self.tokens:  # subtokens
                yield from internal_token.plain_vertical(original_tag)
            yield '</phr>'
        elif self.new_tag and self.new_tag != self.original_tag:
            yield '\t'.join((self['word'] or '', self['lemma'] or '', tag,
                             self.new_tag))
        else:
            yield '\t'.join((self['word'] or '', self['lemma'] or '', tag))

        if not self.trailing_whitespace and not self.final:
            yield '<g/>'

    def parsed_vertical(self):
        # TODO: přepsat podle plain_vertical na generátor
        # TODO: MWE
        # TODO: závislosti
        glue = '' if self.trailing_whitespace else '\n<g/>'
        return '\t'.join((self.get('word', ''), self.get('lemma', ''),
                          self.tag, str(self.begin))) + glue

    @property
    def clean_tag(self):
        # jenom jednoznačný
        return ''.join(attr.attr + attr.value for attr in self.attrs_fixed[2:]
                       if attr and (attr.value != '?' or attr.attr == 'k'))

    def append_internal_token(self, token):
        self.tokens.append(token)
        self.original_lines.extend(token.original_lines)

    def join_internal_tokens(self):
        words = []
        for token in self.tokens:
            words.append(token['word'])
            if token.trailing_whitespace and not token.final:
                words.append(' ')
        return ''.join(words)

    @classmethod
    def from_Token(cls, token, **kwargs):
        attrs = dict(token.items())
        clone = Token(begin=token.begin, **attrs)
        clone.update(kwargs)
        return clone

    @classmethod
    def from_XmlTag(cls, xml_tag):
        return Token(original_lines=xml_tag.original_lines, word=xml_tag['w'],
                     lemma=xml_tag['l'], tag=xml_tag['t'], tokens=[],
                     begin=xml_tag.token_number, modified_by=[
                        value for (attr, value) in xml_tag.attributes
                        if attr == 'modified_by'],
                     use_internal_tokens=('use_internal_tokens', 'true') in
                     xml_tag.attributes, new_tag=xml_tag['new_tag'] or
                     xml_tag['t'])

    @classmethod
    def from_line(cls, line, parse_token, line_number=None):
        attrs = parse_token(line)
        return Token(**attrs, original_lines=[(line_number, line)])

    def set_modified_by(self, modifier, print_original_tag=True):
        """
        Abuse <phr> tag to carry information about modifications to the token.
        """
        # Create fake <phr/> if necessary.
        if not self.tokens:
            self.tokens = [self.from_Token(self)]

        self.modified_by.append(modifier)
        self.print_original_tag = print_original_tag

    lines = plain_vertical


class RuleSymbol(Attrs):
    def __init__(self, other=None, phrase=None, optional=None, head=None,
                 dep=None, **kwargs):
        if isinstance(other, str):
            symbols = read_rule(other, rule_symbol_type=type(self))
            try:
                other = next(symbols)
            except StopIteration:
                raise ValueError('No symbol passed: "' + other + '"')
            # '•' neprojde
            extra = list(symbols)
            if extra:
                # TODO: taky ValueError?
                log.warning('Extra symbols passed, ignoring them: %s',
                            ' '.join(str(t) for t in extra))

        super().__init__(other, **kwargs)
        # název neterminálu
        self.phrase = phrase if other is None else other.phrase
        # zda pro něj existuje ε-pravidlo
        self.optional = optional if other is None else other.optional
        # jestli je hlavou fráze
        self.head = head if other is None else other.head
        # jakou relaci má k hlavě fráze
        self.dep = dep if other is None else other.dep

    def __format__(self, format_spec=''):
        phrase_head = [self.phrase] if self.phrase else []
        is_head = ['head'] if self.head else []
        dependency = ['dep=' + escape(self.dep)] if self.dep else []
        attrs = (attr + '=' + escape(self[attr]) for attr in ATTRS
                 if attr in self and self[attr])
        # extra =
        optional = '?' if self.optional else ''
        return '(' + ' '.join(attr_value for attr_value in chain(
            phrase_head, is_head, attrs, dependency)) + ')' + optional

    def __str__(self):
        return format(self)

    def __repr__(self):
        return 'RuleSymbol(' + escape(self) + ')'


class EdgeSymbol(Attrs):
    """
    Využít Attrs:
    – attrs_fixed zdědit od RuleSymbolu
    – při inicializaci od Tokenu nahradit odpovídající páry (nasdílet je)
    – při zápisu do atributů (gramatická shoda jako nános) nezapisovat přímo
      do párů, ale založit nové
    – tak se vyhnu šílenému skládání při shodě i při str()
    – možná to půjde použít i pro ambiguous a extra
    """
    def __init__(self, other=None, rule_symbol=None, edge=None, **kwargs):
        if other is not None:
            super().__init__(other)
        elif rule_symbol is not None:
            super().__init__(rule_symbol)
        # odpovídající symbol z pravidla
        self.rule_symbol = rule_symbol if other is None else other.rule_symbol
        # odkazovaná hrana (Edge); terminál (Token); None
        self.edge = other.edge if other is not None and edge is None else edge
        if edge is not None:
            self.inherit_attrs()
        self.update(kwargs)

    def inherit_attrs(self):
        # pozor, Edge to má jinde
        for attr_pair in self.edge.attrs_nonempty:
            existing = self.attrs_fixed[attr_pair.attr_id]
            if existing is None:
                self.attrs_nonempty.append(attr_pair)
            self.attrs_fixed[attr_pair.attr_id] = attr_pair
        # TODO: edge.extra? určitě!

    def __setitem__(self, key, value):
        attr_id = ATTR_MAP.get(key)
        if attr_id is not None:
            existing = self.attrs_fixed[attr_id]
            attr_pair = Attr(value, attr_id)  # TODO: aktualizovat podle Attrs
            if existing is None:
                self.attrs_nonempty.append(attr_pair)
            self.attrs_fixed[attr_id] = attr_pair
        else:
            self.extra[key] = value

    @property
    def begin(self):
        return self.edge.begin if self.edge else None  # číslo prvního tokenu

    @property
    def length(self):
        return self.edge.length if self.edge else None  # zahrnutých tokenů

    @property
    def end(self):
        return self.edge.begin + self.edge.length if self.edge else None

    def __eq__(self, other):
        # NE
        # if isinstance(other, str):
        #     return False
        if self.begin != other.begin or self.length != other.length:
            return False
        elif super().__neq__(other):  # WTF?
            return False
        # rekurze: hrany se mohou lišit „pod kapotou“: např. CONSTITUENTS
        # zahrnují CONSTITUENT, ale ten se skládá ze všeho možného
        return self.edge == other.edge
        # TODO: porovnávat Tokeny? ty není potřeba porovnávat, protože máme
        # ty samé, ne?

    def __ne__(self, other):
        return not self.__eq__(other)

    def __format__(self, format_spec=''):  # 's' for (equal) span
        equal_span = 's' in format_spec

        phrase_head = ([self.rule_symbol.phrase] if self.rule_symbol.phrase
                       else [])
        is_head = ['head'] if self.rule_symbol.head else []
        dependency = (['dep=' + escape(self.rule_symbol.dep)]
                      if self.rule_symbol.dep else [])

        attr_ids = ATTR_IDS
        attrs = (ATTRS[attr_id] if self.attrs_fixed[attr_id].value is True
                 else ATTRS[attr_id] + '=' +
                 escape(self.attrs_fixed[attr_id].value)
                 for attr_id in attr_ids if self.attrs_fixed[attr_id])

        span = ['%s–%s' % (self.begin, self.end)] if (
            self.length is not None and (self.length or equal_span)) else []
        optional = '?' if self.rule_symbol.optional else ''
        return '(' + ' '.join(attr_value for attr_value in chain(
            phrase_head, is_head, attrs, dependency, span)) + ')' + optional

    def __str__(self):
        return format(self, 's')

    def __repr__(self):
        return 'EdgeSymbol(' + escape(self) + ')'


class Symbols(list):
    """Abstrakce pro pravou stranu pravidla/hrany (anebo její část)"""
    def __init__(self, iterable=None, position=None, *, symbol_type=Symbol):
        self.symbol_type = symbol_type

        self.position = position
        self.stringified = None
        if isinstance(iterable, str):
            self.extend(read_rule(iterable, rule_symbol_type=self.symbol_type))
        elif iterable is not None:
            super().__init__(iterable)
        else:
            super().__init__()

    def __add__(self, value):
        if isinstance(value, self.symbol_type):
            self.append(value)
        elif isinstance(value, str):
            self.extend(Symbols(value, symbol_type=self.symbol_type))
        else:
            return super().__add__(value)

    def __format__(self, format_spec=''):
        if not self:
            return 'ε' if self.position is None else 'ε •'

        # if self.position is None or format_spec is None:
        symbols = [format(symbol, format_spec) for symbol in self]
        if self.position is not None:
            symbols.insert(self.position, '•')
        # remove empty phrases
        if 'r' in format_spec:
            symbols = [symbol for symbol in symbols if '–' in symbol or
                       symbol == '•']
        return ' '.join(symbols)
        # else:
        #     symbols = [(str(symbol) if index == self.position or
        #                 symbol.length else '') for index, symbol
        #                in enumerate(self)]
        #     symbols.insert(self.position, '•')
        #     return ' '.join(symbol for symbol in symbols if symbol)

    def __str__(self):
        if self.stringified is None:
            self.stringified = format(self)
        return self.stringified

    def __repr__(self):
        return 'Symbols(' + escape(self) + ')'

    def replace_symbol(self, position):
        self[position] = self.symbol_type(self[position])


def read_rule(rule, rule_symbol_type=Symbol):
    """
    Return a list of symbols, i.e. (non-)terminals from a string
    (which has already been split to the left/right side)
    """
    if rule.strip() == 'ε':
        return

    symbol = None  # not None ⇔ inside the symbol
    head = False  # expecting the phrase head (or nothing)
    attr = ''  # a = plus an attribute value may follow
    equal_sign = False  # we are expecting a value for an attribute after =
    closed = False  # the symbol has already ended with )

    for token in shlex(rule, posix=True):
        if token == '(' or (token == '•' and (symbol is None or closed)):
            if symbol is not None:
                yield symbol
                if not closed:  # TODO: allow ambiguous (a=( b=1) ?
                    raise ValueError('Unexpected "("')

            if token == '•':
                yield '•'
                symbol = None
                continue

            symbol = rule_symbol_type()  # TODO: to bude nejčastěji RuleSymbol
            head = closed = False
        elif token == '?':
            symbol.optional = True
        elif token == ')':
            if equal_sign:
                raise ValueError('Unterminated attribute ' + attr)
            elif attr == 'head':
                symbol.head = True
            elif attr:
                symbol[attr] = True  # shodový atribut

            attr = ''
            equal_sign = False
            closed = True
        elif closed:
            raise ValueError('Not expected outside a symbol: ' + token)
        elif not attr:
            if token == '=':
                raise ValueError('Unexpected "="')
            elif not head and token[0].isupper():
                head = symbol.phrase = token
                continue
            attr = token
        elif token == '=':
            equal_sign = True
        elif equal_sign:
            if attr == 'dep':
                symbol.dep = token
            elif attr == 'head':
                symbol.head = token  # stačil by bool
            else:
                symbol[attr] = token
            attr = ''
            equal_sign = False
        else:
            if attr == 'head':
                symbol.head = True
            else:
                symbol[attr] = True
            attr = token

    if symbol is not None:
        yield symbol
        if not closed:
            raise ValueError('Rule not terminated by ")"')


def attr_contains_value(attr):
    return attr is not None and attr.value is not True


def pairs(tag):
    chars = iter(tag)
    for char in chars:
        yield char + next(chars)


def get_symbol_type(name):
    if name == 'Symbol':
        return Symbol
    elif name == 'Token':
        return Token
    elif name == 'RuleSymbol':
        return RuleSymbol
    elif name == 'EdgeSymbol':
        return EdgeSymbol
    else:
        raise RuntimeError('Unknown symbol type: {}'.format(name))
