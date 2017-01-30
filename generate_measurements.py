#!/usr/bin/env python3
from collections import OrderedDict
import subprocess

import models


LEXICON = 'rftagger-lexicon=/home/xsvobo15/tagsetbench/rftagger-external-lexicon-majka.vert'


def k6k9(reference='lexicon-ctx-5-lowercase'):
    words = """
        již, prostě, právě, potom, také, ještě, jasně, jistě, jen, zvláště,
        jenom, bohužel, už, až, především, většinou,
        třeba, možná, tak, zrovna, hlavně, vlastně, jak, co,
        taky, pak, teprve, zvlášť, zvláště, opravdu, nakonec, tu, mimochodem,
        a to, mimo jiné, spíš, též, rovněž, tak
        """.split(',')
    # $ grep -P -i '^(přičemž|nijak|třeba|možná|nejvýš|hlavně|vlastně)' desam.vert | sort | uniq
    NE = """
    nejvýš	nejvýš	k6eAtMd1
    nijak	nijak	k6eAd1
    přičemž	přičemž	k6eAyRd1
    víceméně	víceméně	k9
    """
    words = frozenset(word.strip().lower() for word in words)
    # for word in words:
    #     subprocess.run(['xdg-open',
    #                     'tagsetbench:run?'
    #                     'MATCH;lc={0};k=6;e=A;d=1;'
    #                     'SET;k=9;DEL;e;d;'
    #                     'COMMON;id={0}-k6eAd1-k9;open=no'.format(word)])
    #     subprocess.run(['xdg-open',
    #                     'tagsetbench:run?'
    #                     'MATCH;lc={0};k=9;'
    #                     'SET;k=6;e=A;d=1;'
    #                     'COMMON;id={0}-k9-k6eAd1;open=no'.format(word)])

    sám_jsem_nekonzistentní = """
    a to	a to	k8xCzX
    a to	a to	k9zX
    mimo jiné	mimo jiné	k6eAtMd1zX
    Mimo jiné	mimo jiné	k6eAtMd1zX
    mimo jiné	mimo jiné	k9zX
    """

    zajímavý = """
    Spíše	spíše	k9
    spíš	spát	k5eAaImIp2nS
    spíš	spíš	k6eAxTd2
    spíš	spíš	k9
    """

    tak = """
    Tak	tak	k6eAxDd1
    tak	tak	k6xM
    tak	tak	k8xC
    tak	tak	k8xS
    tak	tak	k9
    """

    alias = reference + '_vs_' + 'k6-k9'
    regex = '|'.join(sorted(words))
    subprocess.run(['xdg-open', """tagsetbench:run?
    external={reference}
    EVALUATE
        bootstrap=no
        {lexicon}
        {context_size}
        {lowercase}
        FILTER;alias=k6-k9
            MATCH;lc={regex};k=6
            # slovo „co“ má k6tQ, takže e=A d=1 není ono
            SET;k=9
            DEL;e;d;y;t;x
            # y kvůli slovu „jak“ (k6eAyQd1)
            # t kvůli slovu „vlastně“ (k6eAtMd1)
            # x kvůli slovu „tak“ (d1eAk6xD)
            # z kvůli mým úpravám (zX)
    COMMON
        id={name}
        corpus-portions=quarters
        open=no""".format(reference=reference,
                          lexicon=LEXICON if 'lexicon' in reference else '',
                          context_size='rftagger-context-length=5',
                          lowercase='rftagger-try-lowercase=yes',
                          regex=regex,
                          name=alias)])

    alias = reference + '_vs_' + 'k9-k6'
    regex = '|'.join(sorted(words))
    subprocess.run(['xdg-open', """tagsetbench:run?
    external={reference}
    EVALUATE
        bootstrap=no
        {lexicon}
        {context_size}
        {lowercase}
        FILTER;alias=k9-k6
            MATCH;lc={regex};k=9
            SET
                k=6
                e=A
                d=1
    COMMON
        id={name}
        corpus-portions=quarters
        open=no""".format(reference=reference,
                          lexicon=LEXICON if 'lexicon' in reference else '',
                          context_size='rftagger-context-length=5',
                          lowercase='rftagger-try-lowercase=yes',
                          regex=regex,
                          name=alias)])


# def punctuation():
#     # TODO: házet do pak nějak do FILTERS (a z toho generovat OrderedDict podle
#     #       id měření nebo aliasu filtru
#     PUNCTUATION = [
#         ('hyphen', '-', 'kIx~'),
#     ]
#     for name, word, tag in PUNCTUATION:
#         subprocess.run(['xdg-open',
#                         'tagsetbench:run?'
#                         'TRAINING_TESTING;bootstrap=no;'
#                         'EVALUATE;'
#                         'TRAINING_TESTING;bootstrap=no;'
#                         'FILTER;silent=yes;'
#                         'MATCH;lc={1};k=\?;'
#                         'SET;tag={2};'
#                         'COMMON;id=punct-{0}'.format(name, word, tag)])


def context_length():
    # rft-train: Error: context length parameter is out of bounds: 0
    for length in range(2, 31):
        subprocess.run(['xdg-open',
                        'tagsetbench:run?'
                        'TRAINING_TESTING;bootstrap=no;'
                        'rftagger-context-length=1;'
                        'EVALUATE;'
                        'TRAINING_TESTING;bootstrap=no;'
                        'rftagger-context-length={0};'
                        'COMMON;id=context-length-{0};open=no'.format(length)])


# elementary/isolated (and please keep it so)
FILTERS = [
    # alias nejde napsat na konec; a s tím mi ani zápis (Ordered)Dict nepomůže
    # – tak leda bych mohl použít COMMON;id= a to pak přenést na alias… když už
    #   tu chci jenom samostatný úpravy – to je univerzální (id jde pak
    #   přeplácnout, alias zůstane)

    # 'FILTER;alias=ordinals;MATCH;word=\d+\.;k=\?;SET;k=4;x=O',
    # 'FILTER;alias=cardinals;MATCH;word=[0-9,.]*\d;k=\?;SET;k=4;x=C',
    # 'FILTER;alias=nejvic;MATCH;lc=nejvíce?;d=1;SET;d=3',
    # # 'FILTER;alias=rok;MATCH;lc=r\.;k=\?;SET;k=1;g=I',
    # 'FILTER;alias=r.;MATCH;lc=r\.;k=\?;SET;k=1;g=I;z=A',
    # 'FILTER;alias=tj.;MATCH;lc=tj\.;k=\?;SET;k=8;x=C;z=A;COMMON;id=tj.',
    # 'FILTER;name=inherit-case-from-preposition',
    # 'FILTER;alias=ordinals-to-adjectives-eAd1;MATCH;k=4;x=O;SET;k=2;e=A;d=1',  # BLBOST: SET;c=1

    # 'FILTER;alias=remove-zA;MATCH;z=A;DEL;z',
    # 'FILTER;alias=revert-to-kA;MATCH;z=A;SET;tag=kA',

    # připraveno
    'FILTER;alias=full-stop;MATCH;word=\.;k=\?;SET;tag=kIx.',
    'FILTER;alias=dash;MATCH;word=-;k=\?;SET;tag=kIx~',

    # vygenerováno, ale asi použiju jen jedno…
    # 'FILTER;alias=passive-participles-to-adjectives;MATCH;k=5;m=N;SET;k=2;e=A;DEL;a;m',
    # 'FILTER;alias=passive-participles-to-adjectives-d1;MATCH;k=5;m=N;SET;k=2;e=A;d=1;DEL;a;m',
    # 'FILTER;alias=passive-participles-to-adjectives-c1;MATCH;k=5;m=N;SET;k=2;e=A;c=1;DEL;a;m',
    'FILTER;alias=passive-participles-to-adjectives-c1d1;MATCH;k=5;m=N;SET;k=2;e=A;c=1;d=1;DEL;a;m',

    # hotovo
    'FILTER;alias=by;MATCH;lc=by|aby|kdyby;DEL;n',
]


# DONE: volitelně porovnávat vůči zvolený bejslajně (místo předchozího řetězu),
#       aby to bylo použitelný i samostatně
def chains(compare_against='baseline', baseline='lexicon-ctx-5-lowercase'):
    for length in range(1, len(FILTERS) + 1):
        chain = models.parse('\n'.join(FILTERS[:length]))
        aliases = [m.params['alias'] for m in chain.sides[0].training_modifications]
        one_less = '\n'.join(';'.join(m.encode()) for m in chain.sides[0].training_modifications[:-1])
        chain = '\n'.join(';'.join(m.encode()) for m in chain.sides[0].training_modifications)

        if compare_against == 'previous':
            # TODO: první ať jde prosím proti externí bejslajně
            reference = one_less
            # aliases = ['previous', 'vs']
            name = 'chain_' + '-'.join(aliases)
        elif compare_against == 'baseline':
            reference = 'external=' + baseline
            name = baseline + '_vs_' + '-'.join(aliases)

        subprocess.run(['xdg-open',
                        'tagsetbench:run?'
                        '{0};'
                        'EVALUATE;'
                        'bootstrap=no;'
                        'rftagger-context-length=5;'
                        'rftagger-try-lowercase=yes;'
                        '{3};'
                        '{1};'
                        'COMMON;id={2};corpus-portions=quarters;'
                        'open=no'.format(reference, chain, name, LEXICON)])


def references():
    for reference in ('unmodified-ctx-5', 'lexicon-ctx-5'):
        for lowercase in ('', 'rftagger-try-lowercase=yes'):
            subprocess.run(['xdg-open',
                            """tagsetbench:run?
    EVALUATE
        bootstrap=no
        {lexicon}
        {context_size}
        {lowercase}
    EVALUATE; # radši stejný
        bootstrap=no
        {lexicon}
        {context_size}
        {lowercase}
    COMMON
        id={name}
        corpus-portions=quarters
        open=no""".format(lexicon=LEXICON if 'lexicon' in reference else '',
                          context_size='rftagger-context-length=5',
                          lowercase=lowercase, name=reference + (
                              '-lowercase' if 'lowercase' in lowercase
                              else ''))])


def isolated(references=[# 'unmodified-ctx-5-lowercase',
                         'lexicon-ctx-5-lowercase']):
    for modifier in FILTERS:
        for reference in references:
            specification = models.parse(modifier)
            model = specification.sides[0].training_modifications[0]
            alias = '{}_vs_{}'.format(reference, model.params.get('alias') or
                                      model.name)
            subprocess.run(['xdg-open',
                            """tagsetbench:run?
    external={reference}
    EVALUATE
        bootstrap=no
        {lexicon}
        {context_size}
        {lowercase}
        {modifier}
    COMMON
        id={name}
        corpus-portions=quarters
        open=no""".format(reference=reference,
                          lexicon=LEXICON if 'lexicon' in reference else '',
                          context_size='rftagger-context-length=5',
                          lowercase='rftagger-try-lowercase=yes',
                          modifier=modifier,
                          name=alias)])


def conditionals(references=[# 'unmodified-ctx-5-lowercase',
                             'lexicon-ctx-5-lowercase']):
    for reference in references:
        alias = '{}_vs_conditionals'.format(reference)
        subprocess.run(['xdg-open',
                        """tagsetbench:run?
    external={reference}
    EVALUATE
        bootstrap=no
        {lexicon}
        {context_size}
        {lowercase}
        FILTER
            alias=by
            MATCH
                k=Y
                lc=by.*
            DEL
                n
                p
                m
            SET
                k=9
                z=Y
        FILTER
            alias=aby-kdyby
            MATCH
                k=Y
                lc=(a|kdy)by.*
            DEL
                n
                p
                m
            SET
                k=8
                z=Y
    COMMON
        id={name}
        corpus-portions=quarters
        open=no""".format(reference=reference,
                          lexicon=LEXICON if 'lexicon' in reference else '',
                          context_size='rftagger-context-length=5',
                          lowercase='rftagger-try-lowercase=yes',
                          name=alias)])


# only external corpora ⇒ time and storage savings
def ad_hoc(left='unmodified-ctx-5-lowercase', right='lexicon-ctx-5-lowercase',
           left_side='reference', right_side='compared'):
    subprocess.run(['xdg-open',
                    """tagsetbench:run?
                    external={0}
                    external-side={1}
                    EVALUATE
                    external={2}
                    external-side={3}
                    COMMON;id={4};corpus-portions=quarters; # quarters first-quarter
                    open=no""".format(left, left_side, right, right_side,
                                      left + '__vs__' + right)])


def rftagger_majka_lexicon():
    subprocess.run(['xdg-open',
                    """tagsetbench:run?
    external=unmodified
    EVALUATE
        bootstrap=no
        rftagger-lexicon=/home/xsvobo15/tagsetbench/rftagger-external-lexicon-majka.vert
    COMMON
        id=unmodified_vs_majka-lexicon
        corpus-portions=quarters
        open=no"""])


def rftagger_wordclass_automaton():
    subprocess.run(['xdg-open',
                    """tagsetbench:run?
    external=unmodified
    EVALUATE
        bootstrap=no
        rftagger-wordclass-automaton=tagsetbench/wordclass_automaton_numbers.txt
    COMMON
        id=unmodified_vs_wordclass-automaton-numbers
        # id=unmodified_vs_regenerated-wordclass-automaton
        corpus-portions=first-quarter
        open=no"""])


def rftagger_try_lowercase(references=['unmodified-ctx-5', 'lexicon-ctx-5']):
    for reference in references:
        subprocess.run(['xdg-open',
                        """tagsetbench:run?
    EVALUATE
        external={reference}
    EVALUATE
        external={reference_lowercase}
    COMMON
        id={reference}_vs_{reference_lowercase}
        corpus-portions=quarters;
        open=no""".format(
            reference=reference,
            reference_lowercase=reference + '-lowercase',
        )])


if __name__ == '__main__':
    # references()
    # isolated()
    chains(compare_against='baseline')
    # k6k9()
    # ad_hoc()
    # rftagger_majka_lexicon()
    # rftagger_wordclass_automaton()
    # rftagger_try_lowercase()
    # conditionals()
