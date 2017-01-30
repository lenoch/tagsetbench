#!/usr/bin/env python3
"""
Preprocessing:
očíslovat, vyčistit a uložit v zjednodušené a čisté struktuře

TODO:
hvězdičky: vyhazovat, když jsou na začátku věty
           měnit na tečku, když jsou uprostřed (i když by bylo lepší
           vytvořit novou větu)
uvozovky: stačí jim kI, anebo potřebujou specifičtější značku? (snadná
          pomoc, přehled značek pro interpunkci přece existuje)
"""
import json
import re
import sys

from tagsetbench import ShellPath, read_args
from vertical import read_vertical

PARAMETERS = {
    'source-corpus': ShellPath(),
    'preprocessed-corpus': ShellPath(),
    'sentence-boundaries': ShellPath(),

    'include-inner': 'false',  # „(obr. 5)“, jinak odstranit
}


def run_bootstrap(argv):
    args = read_args(argv, PARAMETERS)
    with args['source-corpus'].open() as source_corpus, \
            args['preprocessed-corpus'].open('w') as preprocessed_corpus:
        for line in bootstrap(args, source_corpus):
            print(line, file=preprocessed_corpus)


def bootstrap(args, lines):
    # TODO: případně podle nějakého atributu
    include_inner = args['include-inner'] == 'true'
    open_tags = []
    sentence_number = 0  # 1-based human-friendly number (see below)
    running_token_count = 0
    running_line_count = 0
    inside_sentence = False
    skip_lines = False
    sentence_boundaries = {}

    for xml_tag, token in read_vertical(lines,
                                        token_parser=parse_token_and_fix):
        if xml_tag:
            if xml_tag.opening:
                # WONT: ale přeskakovat ty <p>, ať můžu zpracovávat starší
                #       verze DESAMu – ne, tím jsem naštěstí začal v 295
                open_tags.append(xml_tag)
                if xml_tag.name in ('s', 'head'):
                    if not inside_sentence:
                        token_count = 0
                        line_count = 0
                        sentence_number += 1
                        xml_tag['number'] = str(sentence_number)
                        inside_sentence = True
                        yield xml_tag
                elif inside_sentence and xml_tag.name in (
                        'table', 'item') and not include_inner:
                    skip_lines = True

            elif open_tags:  # xml_tag.closing == True
                opening = open_tags.pop()
                if xml_tag.name == opening.name:
                    if opening.name in ('s', 'head') and opening['number']:
                        inside_sentence = False
                        yield xml_tag

                        starting_line = running_line_count + (
                            2 * (sentence_number - 1))  # <s> and </s> for each

                        sentence_boundaries[sentence_number] = {
                            'starting-line': starting_line,
                            'lines': line_count,
                            # TODO: preceding-tokens
                            'total-tokens': token_count + running_token_count,
                        }

                        running_token_count += token_count
                        running_line_count += line_count
                    elif inside_sentence and xml_tag.name in (
                            'table', 'item'):
                        # už se přeskočil obsah table/item
                        skip_lines = False
                else:
                    raise ValueError(
                        'překřížení: {} místo uzavření {}      {}'.format(
                             xml_tag.original_lines[0],
                             '?!' if not open_tags else open_tags[-1],
                             open_tags))
            else:
                raise ValueError('osamocená uzavírací značka: '
                                 '{}'.format(xml_tag))
        elif not skip_lines and inside_sentence:
            token_count += 1
            for count, line in enumerate(token.plain_vertical(), 1):
                yield line
            line_count += count

    if args['sentence-boundaries']:
        args['sentence-boundaries'].write_text(json.dumps(
            sentence_boundaries, indent=4, sort_keys=True))


def parse_token_and_fix(line):
    columns = line.split('\t')

    if len(columns) >= 3:
        word, lemma, tag, *extra = columns
        if extra:
            log.warning('Too many columns: %s', line)

    else:  # two columns (word + lemma/tag) don't exist in the data
        word = lemma = line
        tag = 'k?'

    return {'word': word, 'lemma': lemma, 'tag': tag}


if __name__ == '__main__':
    run_bootstrap(sys.argv)
