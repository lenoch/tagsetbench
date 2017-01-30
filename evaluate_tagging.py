#!/usr/bin/env python3
from collections import namedtuple, OrderedDict
import json
from pathlib import PosixPath
import re
import sys

import html_writer
import models
from symbols import pairs
from tagsetbench import read_args
from vertical import parse_token_with_two_tags, read_sentences

Row = namedtuple('Row', ['expected_tag', 'given_tag', 'word',
                         'reference_count', 'compared_count'])


# seřazeno, jen to teď nevypadá tak hezky
ERROR_GROUPS = OrderedDict([
    # whole tag (total error rate)
    ('tag', [
        ({}, {}),
    ]),


    # errors in case (homonymy)
    ('case', [
        # c1 c[427365]
        # c2 c[4637]
        # c4 c[673]
        # c3 c[67]
        # c6 c7
        ({'c': '.'}, {'c': '.'}),
    ]),
    ('c1 / c4', [
        # (expected, got)
        ({'c': '[14]'}, {'c': '[14]'}),
    ]),

    # to, které, který, co, …
    # ('c1 k3 / c4', [
    #     # (expected, got)
    #     ({'c': '1', 'k': '3'}, {'c': '4'}),
    #     ({'c': '4', 'k': '3'}, {'c': '1'}),
    # ]),
    # TODO: jo aha, ono to filtruje asi jenom v rozdílu :-(
    # TODO: takže zatím prostě ty seznamy slov rozdělit podle značek…
    # 	k3gNnSc1xD	k3gNnSc4xD	Toto, to, toto	62	61	0.025%	0.025%	6.217%	5.133%

    ('c4 / c2', [
        ({'c': '[42]'}, {'c': '[42]'}),
    ]),
    ('c1 / c2', [
        ({'c': '1'}, {'c': '2'}),
        ({'c': '2'}, {'c': '1'}),
    ]),
    ('c6 / c4', [
        ({'c': '6'}, {'c': '4'}),
        ({'c': '4'}, {'c': '6'}),
    ]),
    # nepřítomnost pádu na jedné/druhé porovnávané straně
    # (ale bez neoznačkovaných slov, těch tam bylo moc; a mám je jinde)
    ('c lost', [
        ({'c': '.'}, {'c': None, 'k': '[0-9AY]'}),
    ]),
    ('c added', [
        ({'c': None, 'k': '[0-9AY]'}, {'c': '.'}),
    ]),
    ('c7 / c4', [
        ({'c': '7'}, {'c': '4'}),
        ({'c': '4'}, {'c': '7'}),
    ]),
    ('c3 / c2', [
        ({'c': '3'}, {'c': '2'}),
        ({'c': '2'}, {'c': '3'}),
    ]),
    ('c6 / c2', [
        ({'c': '6'}, {'c': '2'}),
        ({'c': '2'}, {'c': '6'}),
    ]),
    ('c3 / c4', [
        ({'c': '3'}, {'c': '4'}),
        ({'c': '4'}, {'c': '3'}),
    ]),
    ('c2 / c7', [
        ({'c': '2'}, {'c': '7'}),
        ({'c': '7'}, {'c': '2'}),
    ]),
    ('c7 / c1', [
        ({'c': '7'}, {'c': '1'}),
        ({'c': '1'}, {'c': '7'}),
    ]),
    ('c3 / c6', [
        ({'c': '3'}, {'c': '6'}),
        ({'c': '6'}, {'c': '3'}),
    ]),
    ('c3 / c1', [
        ({'c': '3'}, {'c': '1'}),
        ({'c': '1'}, {'c': '3'}),
    ]),
    ('c6 / c1', [
        ({'c': '6'}, {'c': '1'}),
        ({'c': '1'}, {'c': '6'}),
    ]),
    ('c7 / c6', [
        ({'c': '7'}, {'c': '6'}),
        ({'c': '6'}, {'c': '7'}),
    ]),


    # errors in number (homonymy)
    ('number', [
        ({'n': '.'}, {'n': '.'}),
    ]),
    ('n added', [
        ({'n': None}, {'n': '.'}),
    ]),
    ('n lost', [
        ({'n': '.'}, {'n': None}),
    ]),


    # errors in gender
    ('gender', [
        ({'g': '.'}, {'g': '.'}),
    ]),
    ('gI / gM', [
        ({'g': 'I'}, {'g': 'M'}),
        ({'g': 'M'}, {'g': 'I'}),
    ]),
    ('gI / gF', [
        ({'g': 'I'}, {'g': 'F'}),
        ({'g': 'F'}, {'g': 'I'}),
    ]),
    ('gF / gM', [
        ({'g': 'F'}, {'g': 'M'}),
        ({'g': 'M'}, {'g': 'F'}),
    ]),
    ('gN / gF', [
        ({'g': 'N'}, {'g': 'F'}),
        ({'g': 'F'}, {'g': 'N'}),
    ]),
    ('gN / gI', [
        ({'g': 'N'}, {'g': 'I'}),
        ({'g': 'I'}, {'g': 'N'}),
    ]),
    ('gN / gM', [
        ({'g': 'N'}, {'g': 'M'}),
        ({'g': 'M'}, {'g': 'N'}),
    ]),
    ('g added', [
        ({'g': None}, {'g': '.'}),
    ]),
    ('g lost', [
        ({'g': '.'}, {'g': None}),
    ]),


    # not very frequent thanks to majka's lexicon
    ('aspect', [
        ({'a': '.'}, {'a': '.'}),  # IBP
    ]),
    ('a added', [
        ({'a': None}, {'a': '.'}),
    ]),
    ('a lost', [
        ({'a': '.'}, {'a': None}),
    ]),
    ('negation', [
        ({'e': '.'}, {'e': '.'}),  # AN
    ]),
    ('e added', [
        ({'e': None}, {'e': '.'}),
    ]),
    ('e lost', [
        ({'e': '.'}, {'e': None}),
    ]),


    # annotation lost (k. → k?)
    ('tag lost', [  # TODO: mám tu i k2zA / k?
        ({}, {'k': r'\?'}),
    ]),
    ('g.nSc1', [
        ({'c': '1', 'n': 'S', 'g': '[MFNI]'}, {}),
    ]),


    # newly annotated (k? → k1)
    ('tag guessed', [
        ({'k': '\?'}, {'k': '[^?]'}),
    ]),
    ('k? → k1', [
        ({'k': '\?'}, {'k': '1'}),
    ]),
    ('k? → k[^12?]', [
        ({'k': '\?'}, {'k': '[^12?]'}),  # [34567890YIA]
    ]),
    ('k? → k2', [
        ({'k': '\?'}, {'k': '2'}),
    ]),


    ('k6 / k9', [
        ({'k': '6'}, {'k': '9'}),
        ({'k': '9'}, {'k': '6'}),
    ]),
    ('k8 / k9', [
        # (expected, got)
        ({'k': '8'}, {'k': '9'}),
        ({'k': '9'}, {'k': '8'}),
    ]),
    ('k8 / k6', [
        ({'k': '8'}, {'k': '6'}),
        ({'k': '6'}, {'k': '8'}),
    ]),
    ('x', [
        ({'x': '.'}, {'x': '.'}),
    ]),
    ('x expected', [
        ({'x': '.'}, {}),
    ]),
    ('t', [  # chyba mezi hodnotama „t“ se neobjevila
        ({'t': '.'}, {}),
        ({}, {'t': '.'}),
    ]),
    ('tM', [
        ({}, {'t': 'M'}),
        ({'t': 'M'}, {}),
    ]),
    ('y', [  # yR / yQ, yI / yR
        ({'y': '.'}, {'y': '.'}),
    ]),
    ('numerals', [
        ({'k': '4'}, {}),
        ({}, {'k': '4'}),
    ]),


    # adjectives
    ('k1 / k2', [
        ({'k': '1'}, {'k': '2'}),
        ({'k': '2'}, {'k': '1'}),
    ]),
    ('k2 / k5', [  # c1d1gFk2 aIk5mIp3
        ({'k': '5'}, {'k': '2'}),
        ({'k': '2'}, {'k': '5'}),
    ]),
    ('passives', [
        ({}, {'m': 'N'}),
        ({'m': 'N'}, {}),
    ]),
    ('ordinals', [  # k4xO (original tags)
        ({'k': '4', 'x': 'O'}, {}),
        ({}, {'k': '4', 'x': 'O'}),
    ]),
    # TODO: hodit asi ke k1 / k2
    # feminine surnames (before the change)
    ('surnames', [  # s word/lemma tady mám smůlu
        ({'k': '1', 'g': 'F'}, {'k': '2'}),
        ({'k': '2'}, {'k': '1', 'g': 'F'}),
    ]),


    # homonymy & perhaps unnecessary distinctions
    ('k1 / k6', [
        ({'k': '1'}, {'k': '6'}),
        ({'k': '6'}, {'k': '1'}),
    ]),
    ('k1 / k7', [
        ({'k': '1'}, {'k': '7'}),
        ({'k': '7'}, {'k': '1'}),
    ]),
    ('k3 / k5', [
        ({'k': '3'}, {'k': '5'}),
        ({'k': '5'}, {'k': '3'}),
    ]),
    ('k6 / k7', [
        ({'k': '6'}, {'k': '7'}),
        ({'k': '7'}, {'k': '6'}),
    ]),
    ('k1 / k5', [  # c1gFk1 aIeAk5mIp3
        ({'k': '1'}, {'k': '5', 'm': '[^N]'}),
        ({'k': '5', 'm': '[^N]'}, {'k': '1'}),
    ]),
    ('k9 / k3', [
        ({'k': '9'}, {'k': '3'}),
        ({'k': '3'}, {'k': '9'}),
    ]),


    # annotation errors
    ('xC / xS', [
        ({'x': 'C'}, {'x': 'S'}),
        ({'x': 'S'}, {'x': 'C'}),
    ]),
    # oboustranně zaměňovanej pozitiv a superlativ (a je jedno, co
    # ostatní atributy, hodit to do jednoho pytle)
    ('degree', [
        ({'d': '.'}, {'d': '.'}),
    ]),
    ('d1 / d3', [
        ({'d': '1'}, {'d': '3'}),
        ({'d': '3'}, {'d': '1'}),
    ]),
    ('d2 / d1', [
        ({'d': '2'}, {'d': '1'}),
        ({'d': '1'}, {'d': '2'}),
    ]),
])


OPTIONS = {
    'reference-corpus': PosixPath(),
    'compared-corpus': PosixPath(),

    'global-settings': PosixPath(),  # klidně stačí 'settings'

    # JSON to decide upon unknown words or non-existent word-tag tuples in the
    # tagging model (unknown-word, known-word-unknown-tag)
    'reference-training-lexicon': PosixPath(),
    'compared-training-lexicon': PosixPath(),

    'attribute': [''],  # e.g. 'k', 'g', 'n', 'c', 'kgnc', …

    'json-summary': PosixPath(),
    'html-summary': PosixPath(),
    # TODO: i Miloš říkal, ať si tabulky s výsledkama generuju přímo z programu
    'latex-summary': PosixPath(),

    'ungrouped-tagging-errors': False,  # ⇒ words to focus on
    'errors-grouped-by-tag': False,  # ⇒ ambiguous attr combinations
    'ungrouped-errors-threshold': 5,
    'grouped-errors-threshold': 10,

    # the testing corpus serving as a reference here (to judge tags
    # assigned to 'tagged-corpus' correct or incorrect)
    # golden-corpus
    # the same textual data, but with tags newly assigned by a tagger
    # (which uses a statistical model built from a training corpus)
    # tagged-corpus

    # JSON containing the lexicon of the testing corpus: to learn about
    # ambiguity, if the two lexicons are joined together
    # 'testing-lexicon': PosixPath(),  # TODO: use this, maybe?
}


class CompareError(Exception):
    pass


class CompareTaggedCorpusAgainstGolden:
    """
    Compare a testing corpus annotated using a model built from a training
    corpus – against a golden testing corpus.
    """
    def __init__(self, argv):
        self.args = read_args(argv, OPTIONS)

        self.global_settings = {}

        # the whole-tag evaluation is compulsory and must happen first
        # (so that total token count is known to other evaluation processes)
        if 'whole-tag' in self.args['attribute']:
            self.args['attribute'].pop(self.args['attribute'].index('whole-tag'))
        self.args['attribute'].insert(0, 'whole-tag')

        # TODO: ukázat, jakou mají strukturu; asi jednoduchou, navíc zřejmě
        #       řeším jen klíče
        # TODO: klíče ⇒ unknown-word, nižší úroveň ⇒ known-word+unknown-tag
        #       nebo taky jednoznačné/nejednoznačné slovo
        self.reference_training_lexicon = {}
        self.compared_training_lexicon = {}

        self.reference_corpus_evaluation = {}
        self.compared_corpus_evaluation = {}
        self.reference_corpus_summary = {}
        self.compared_corpus_summary = {}

        self.summary = {
            # TODO: možná nějak rozpadnout, použít přímo self.args['x']
            'argv': self.args['argv'],
            # TODO: chci tu i podrobný informace o hodnocených korpusech včetně
            #       kontrolních součtů nebo revizí v Gitu, to samé o programech
            # TODO: začít můžu třeba úpravama (názvama i volbama) a o jaké
            #       rozdělení jde
            'reference': self.reference_corpus_summary,
            'compared': self.compared_corpus_summary,
            'difference': {},  # TODO
        }

        # If self.training_lexicon is not used, self.unknown_words and
        # self.unknown are untouched, as well as self.wrong_unknown_words
        # self.wrong_unknown_words = 0  # TODO: redo
        # self.unknown_words = {}  # TODO: k čemuže přesně to je, a strukturu?
        # self.unknown = {}  # TODO: stejná otázka → přejmenovat, fuj

    def compare_corpus_against_reference_corpus(self):
        self.prepare()
        self.run_evaluate()
        self.summarize_and_compare()
        self.save_summary_results()
        if self.args['ungrouped-tagging-errors'] or \
                self.args['errors-grouped-by-tag']:
            self.work_out_tagging_errors()  # jsme zpátky!

    def prepare(self):
        if self.args['global-settings'].name:  # settings.json
            with self.args['global-settings'].open() as f:
                self.global_settings = json.load(f)

            self.specification = models.parse(self.global_settings.get(
                'specification'))  # měl jsem i název comparison

        if self.args['reference-training-lexicon'].name:
            with self.args['reference-training-lexicon'].open() as f:
                self.reference_training_lexicon = json.load(f)

        if self.args['compared-training-lexicon'].name:
            with self.args['compared-training-lexicon'].open() as f:
                self.compared_training_lexicon = json.load(f)

    def run_evaluate(self):
        """
        Feed the main procedure with two corpora. The division of labour among
        two function was made to test the inner function.
        """
        with self.args['reference-corpus'].open() as reference_corpus, \
                self.args['compared-corpus'].open() as compared_corpus:
            reference_sentences = read_sentences(
                reference_corpus, token_parser=parse_token_with_two_tags)
            compared_sentences = read_sentences(
                compared_corpus, token_parser=parse_token_with_two_tags)

            self.evaluate(reference_sentences, compared_sentences)

    def evaluate(self, reference_sentences, compared_sentences):  # compare
        # Walk over all sentences in the compared corpora (the reference/golden
        # one and the tagged one).
        for reference_sentence in reference_sentences:
            compared_sentence = next(compared_sentences)  # TODO: zip_longest?

            reference_sentence.check_match(compared_sentence)
            # self.total_tags += len(reference_sentence.tokens)

            # Sentence numbers match, as well as token counts, let’s compare.
            self.compare_sentence(
                reference_sentence.tokens, compared_sentence.tokens,
                reference_sentence.opening_tag['number'])

    def compare_sentence(self, reference_tokens, compared_tokens,
                         sentence_number=None):
        compared_tokens = iter(compared_tokens)
        for reference_token in reference_tokens:
            compared_token = next(compared_tokens)

            word = reference_token['word']
            if word != compared_token['word']:
                raise CompareError("Words don’t match: '{}' vs. '{}'".format(
                    word, compared_token['word']))

            self.evaluate_tag_against_golden(
                reference_token, self.reference_corpus_evaluation)
            self.evaluate_tag_against_golden(
                compared_token, self.compared_corpus_evaluation)

            # TODO: use_internal_tokens by to mělo asi nastavovat taky, aby to
            #       šlo tady poznat
            if reference_token.modified_by or compared_token.modified_by:
                # TODO: dávat snad to změněný do 'whole-tag-direct' :-)
                pass  # modified_by je seznam změn provedených na tokenu
            else:
                self.evaluate_tag_against_golden(
                    reference_token, self.reference_corpus_evaluation,
                    indirect=True)
                self.evaluate_tag_against_golden(
                    compared_token, self.compared_corpus_evaluation,
                    indirect=True)

        # TODO: sentence accuracy pro všechny sledovaný kombinace atributů?

    def evaluate_tag_against_golden(self, token, evaluation, indirect=False):
        if token.use_internal_tokens:
            for internal_token in token.tokens:
                self.compare_tag(internal_token, evaluation, indirect)
        else:
            self.compare_tag(token, evaluation, indirect)

    def compare_tag(self, token, evaluation, indirect):
        golden_attrs = token
        tagged_attrs = token.new_tag_fake_token

        for attrs in self.args['attribute']:
            if len(attrs) == 1 or attrs == 'whole-tag':
                self.compare_attribute(evaluation, golden_attrs, tagged_attrs,
                                       attrs, indirect)
            else:
                self.compare_attributes(evaluation, golden_attrs, tagged_attrs,
                                        attrs, indirect)

    # TODO: místo týhle složitosti bych možná radši měl počítat přímo 'total'
    #       a 'correct'; a přesunout ji do starýho kódu
    def compare_attribute(self, evaluation, golden_attrs, tagged_attrs, attr,
                          indirect):
        if attr == 'whole-tag':
            expected_value = golden_attrs.tag
            given_value = tagged_attrs.tag
        else:
            expected_value = golden_attrs.get(attr, '')
            given_value = tagged_attrs.get(attr, '')

        if not expected_value and not given_value:
            return

        # add the attribute to the dictionary
        if indirect:
            # TODO: sufixovat asi vždycky: 'all', 'indirect' a 'direct' (nebo
            #       'affected', 'changed', 'modified', …)
            attr = attr + '-indirect'
        expected_values = evaluation.setdefault(attr, {})

        # add the expected value as a nested dictionary
        given_values = expected_values.setdefault(expected_value, {})

        # add the given value as a nested dictionary
        words = given_values.setdefault(given_value, {})

        # TODO: nešlo by to slovo získávat dřív, společně?
        # increase the count of the word (or actually the count of the word,
        # expected value, given value combination)
        word = golden_attrs['word']
        if word in words:
            words[word] += 1
        else:
            words[word] = 1

        # TODO: rozpadnout to ještě podle celých tagů?

    def compare_attributes(self, evaluation, golden_attrs, tagged_attrs, attrs,
                           indirect):
        golden_values = []
        tagged_values = []

        for attr in attrs:
            golden_values.append(golden_attrs.get(attr, ' '))
            tagged_values.append(tagged_attrs.get(attr, ' '))

        expected_value = ''.join(golden_values)
        given_value = ''.join(tagged_values)

        # add the attribute to the dictionary
        if indirect:
            # TODO: sufixovat asi vždycky: 'all', 'indirect' a 'direct' (nebo
            #       'affected', 'changed', 'modified', …)
            attrs = attrs + '-indirect'
        expected_values = evaluation.setdefault(attrs, {})

        # add the expected value as a nested dictionary
        given_values = expected_values.setdefault(expected_value, {})

        # add the given value as a nested dictionary
        words = given_values.setdefault(given_value, {})

        # TODO: nešlo by to slovo získávat dřív, společně?
        # increase the count of the word (or actually the count of the word,
        # expected value, given value combination)
        word = golden_attrs['word']
        if word in words:
            words[word] += 1
        else:
            words[word] = 1

    def summarize_and_compare(self):
        # TODO: Jo, summarize? Teda jinak: ať hlavně tenhle vyhodnocovač spočte
        #       hlavně přehled a uloží ho v JSONu a HTML (a pak možná i LaTeXu)
        #       a předá ten JSON dál. Potřebuju nejdřív mít všechno to vyhodno-
        #       cení a až potom se můžu zabejvat nějakým podrobným zkoumáním.
        self.summarize(self.reference_corpus_evaluation,
                       self.reference_corpus_summary)
        self.summarize(self.compared_corpus_evaluation,
                       self.compared_corpus_summary)
        self.compute_differences()  # compared-minus-reference

    def summarize(self, evaluation, summary):
        for attrs, expected_values in evaluation.items():
            total_values = 0
            correct_values = 0

            # import rpdb2; rpdb2.start_embedded_debugger('123')

            for expected_value, given_values in expected_values.items():
                for given_value, words in given_values.items():
                    words_count = 0  # TODO: přepsat tohle dole na sum()?

                    for word, counts in words.items():
                        words_count += counts

                    total_values += words_count
                    if given_value == expected_value:
                        correct_values += words_count

            summary[attrs] = {
                'total': total_values,
                'correct': correct_values,
                'precision': '{:0.3%}'.format(correct_values / total_values) if
                total_values else 'N/A',
                'global-accuracy': 'N/A',  # TODO (bude to chtít celkovej počet tokenů)
            }

    def compute_differences(self):
        for attrs, reference_summary in self.reference_corpus_summary.items():
            compared_summary = self.compared_corpus_summary[attrs]

            self.summary['difference'][attrs] = {
                'total': (compared_summary['total'] -
                          reference_summary['total']),
                'correct': (compared_summary['correct'] -
                            reference_summary['correct']),
                'precision': '{:0.3%}'.format(
                    compared_summary['correct'] / compared_summary['total'] -
                    reference_summary['correct'] / reference_summary['total'])
                if reference_summary['total'] and compared_summary['total']
                else 'N/A',
                'global-accuracy': 'N/A',  # TODO
            }

    def save_summary_results(self):
        # TODO: proč to musí trvat minutu a půl, než se sem dostanu?

        if self.args['json-summary'].name:
            self.save_json_summary()

        if self.args['html-summary'].name:
            self.print_html_summary()

    def save_json_summary(self):
        """
        {
            "whole-tag": {
                "correct": 209158,
                "precision": "85.959%",
                "total": 243323
            }
        }
        """
        with self.args['json-summary'].open('w') as summary:
            json.dump(self.summary, summary, indent=4, sort_keys=True,
                      ensure_ascii=False)

    def print_html_summary(self):
        # title = '{} vs. {} ({})'.format(
        #     self.args['reference-corpus'],
        #     self.args['compared-corpus'],
        #     ', '.join(self.args['attribute']),
        # )

        # if 'whole-tag' in self.args['attribute']:
        #     # protože chci ještě nepřímou přesnost na atributech (a jejich
        #     # kombinacích), větách a co já vím ještě
        #     direct_whole_tag_token_precision = (
        #         self.evaluation['whole-tag']['correct'] /
        #         self.evaluation['whole-tag']['total'])
        #
        #     title = '{:0.3%} – {}'.format(
        #         direct_whole_tag_token_precision, title)

        title = self.specification.options['id']

        # TODO: description
        # TODO: zpětnej odkaz (ten by měl jít asi nějak jednoduše udělat,
        #       prostě se dá pokusy.html#alias
        # TODO: odkazy na tabulky chyb?
        # TODO: odkaz na spouštěč a na zdroják?
        # TODO: prostě moje záhlaví?

        with self.args['html-summary'].open('w') as summary:
            print(html_writer.header(title, argv=self.args['argv']),
                  file=summary)

            print('<table>', file=summary)
            # TODO: indirect fakt radši dávat na další řádek, ať se mi to
            #       zkrátí
            # TODO: počet vět, počet správných vět, sentence precision…
            for side in ('reference', 'compared', 'difference'):
                for line in html_writer.evaluation_summary(
                        side, self.summary[side]):
                    print(line, file=summary)

            print('</table>', file=summary)
            print(html_writer.after_content, file=summary)

        with self.args['html-summary'].with_suffix('.vertical.html').open('w') as summary:
            print(html_writer.header(title, argv=self.args['argv']),
                  file=summary)

            print('<table>', file=summary)
            # tady z toho lezou attrs: a, a-indirect, c, c-indirect, …
            # direct (modified tokens), indirect (unmodified), total (all)
            for attr, values in sorted(self.summary['reference'].items()):
            # TODO: arbitrární řazení atributů (v pořadí, jak jsem je
            #       definoval, abych měl nahoře/nejdřív ty, co mě zajímaj)
                if not isinstance(values, dict):
                    continue
                for line in html_writer.evaluation_summary_sides_horizontal(
                        attr, self.summary):
                    print(line, file=summary)

            print('</table>', file=summary)
            print(html_writer.after_content, file=summary)

    def work_out_tagging_errors(self):
        # TODO: pouštět to tady pro whole-tag-indirect (bez změn) a pro tu
        #       srandu i pro whole-tag-direct (jen změněný); pro -all to asi
        #       nemá smysl
        for attribute in ('whole-tag',):
            if attribute not in self.reference_corpus_evaluation or \
                    attribute not in self.compared_corpus_evaluation:
                continue

            merged_evaluation = {}
            self.prepare_unsorted_errors(
                self.reference_corpus_evaluation[attribute], merged_evaluation,
                'reference')
            self.prepare_unsorted_errors(
                self.compared_corpus_evaluation[attribute], merged_evaluation,
                'compared')
            unsorted_errors = self.list_unsorted_errors(merged_evaluation)
            self.save_ungrouped_tagging_errors(unsorted_errors, attribute)
            self.save_tagging_errors_grouped_by_tag(unsorted_errors, attribute)
            self.save_errors_by_tag_difference(unsorted_errors, attribute)

    def prepare_unsorted_errors(self, evaluation, merged_evaluation,
                                reference_or_compared):
        # TODO: oba korpusy poslat do funkce, co to všechno nahází do
        #       dalšího velkýho slovníku
        # TODO: ale na to, abych dal dohromady oba korpusy, je přece jenom
        #       dobrý používat slovníky: hlavně na to, abych mohl přidat jednu
        #       nebo druhou vyhodnocovanou stranu, ale vůbec i na to, abych je
        #       měl kam vkládat
        for expected_tag, given_tags in evaluation.items():
            merged_given_tags = merged_evaluation.setdefault(expected_tag, {})

            for given_tag, words in given_tags.items():
                if given_tag == expected_tag:
                    continue

                # TODO: tady bych klidně mohl teda počítat ten rozdíl mezi
                #       značkama (ten první výstup, co jsem si napsal do Gitu,
                #       protože mi to spadlo na 'compared_corpus' místo
                #       'compared_counts', ukazoval rozdíl v pádu (c7 místo c3)
                #       u slova „jí“

                merged_words = merged_given_tags.setdefault(given_tag, {})

                for word, count in words.items():
                    compared_counts = merged_words.setdefault(word, {})

                    # ⇒ {'reference': 123, 'compared': 234} for each word, for
                    # each wrong tag, for each expected tag
                    compared_counts[reference_or_compared] = count

    def list_unsorted_errors(self, merged_evaluation):
        # TODO: a pak to z něj vypíšu do tabulky a tu už si můžu řadit jak chci
        unsorted_errors = []

        for expected_tag, given_tags in merged_evaluation.items():
            for given_tag, words in given_tags.items():  # always a wrong tag
                for word, reference_and_compared_counts in words.items():
                    word_unknown_combinations = \
                        self.decide_if_word_tag_is_unknown(word, expected_tag)
                    if word_unknown_combinations:
                        # MAYBE: title=""
                        word = '<span class="{}">{}</span>'.format(' '.join(
                            word_unknown_combinations), word)
                    unsorted_errors.append(Row(
                        expected_tag,  # Cheap Trick – If You Want My Love
                        given_tag,  # zněj trochu jako Beatles
                        word,
                        reference_and_compared_counts.get('reference', 0),
                        reference_and_compared_counts.get('compared', 0),
                    ))
        return unsorted_errors

    def decide_if_word_tag_is_unknown(self, word, expected_tag):
        word_unknown_combinations = []

        # NOTE: když mám na jedné straně porovnání to slovo celé neznámé a na
        #       druhé má jiné značky, jen ne tuhle správnou, tak se to zobrazí
        #       jako neznámý slovo (když náááhodou budu chtít, tak si můžu
        #       doplnit nějakou vysvětlivku, jak to je opravdu)

        if (word not in self.reference_training_lexicon or
                word not in self.compared_training_lexicon):
            word_unknown_combinations.append(
                'uw')  # unknown-word
        elif (expected_tag not in self.reference_training_lexicon[word] or
                expected_tag not in self.compared_training_lexicon[word]):
            word_unknown_combinations.append(
                'kwut')  # known-word-unknown-tag

        return word_unknown_combinations

    def save_ungrouped_tagging_errors(self, unsorted_errors, attribute):
        errors_above_threshold = filter(
            lambda row: max(row[3], row[4]) >=
            self.args['ungrouped-errors-threshold'], unsorted_errors)

        ungrouped_errors = sorted(
            errors_above_threshold, key=lambda row:
            (max(row[3], row[4]), row[3], row[4]), reverse=True)

        # ⇒ words to focus on
        with open('errors-ungrouped-{}.html'.format(attribute),
                  'w') as summary:
            print(html_writer.header(
                'Tagging errors sorted by reference, '
                'compared, both descending', argv=self.args['argv'],
                ), file=summary)

            for line in html_writer.simple_table(ungrouped_errors, [
                    'Expected', 'Got', 'Word', 'Reference count',
                    'Compared count']):
                print(line, file=summary)

            print(html_writer.after_content, file=summary)

    def save_tagging_errors_grouped_by_tag(self, unsorted_errors, attribute):
        # TODO: jo, spojovat prostě řádky, co maj stejný tagy a jiný slova
        #       (ideální aplikace pro sqlite3 – pokud teda umí CONCAT na
        #       více hodnotách – prostě s ', ')

        # group tags first (by simply sorting the list by tags)
        pregrouped_errors = list(sorted(
            unsorted_errors, key=lambda row:
            (row[0], row[1]), reverse=True))

        # join words in consecutive rows if tags match
        errors_grouped_by_tag = []
        last_tag_tuple = None
        for row in pregrouped_errors:  # sorted by tags now
            (expected_tag, given_tag, word, reference_count,
             compared_count) = row
            tag_tuple = expected_tag, given_tag
            if tag_tuple == last_tag_tuple:
                last_row = list(errors_grouped_by_tag[-1])
                last_row[2] += ', {}'.format(word)
                last_row[3] += reference_count
                last_row[4] += compared_count
                errors_grouped_by_tag[-1] = last_row
            else:
                errors_grouped_by_tag.append(row)
            last_tag_tuple = tag_tuple

        errors_above_threshold = filter(
            lambda row: max(row[3], row[4]) >=
            self.args['grouped-errors-threshold'], errors_grouped_by_tag)

        errors_grouped_by_tag = list(sorted(
            errors_above_threshold, key=lambda row:
            (max(row[3], row[4]), row[3], row[4]), reverse=True))

        errors_grouped_by_tag_with_running_counts_and_percentage = []
        running_count_reference = running_count_compared = 0

        # reference_errors_count = (
        #     self.summary['reference'][attribute]['total'] -
        #     self.summary['reference'][attribute]['correct'])
        # compared_errors_count = (
        #     self.summary['compared'][attribute]['total'] -
        #     self.summary['compared'][attribute]['correct'])
        reference_tokens_count = self.summary['reference'][attribute]['total']
        compared_tokens_count = self.summary['compared'][attribute]['total']

        for row in errors_grouped_by_tag:
            running_count_reference += row[3]
            running_count_compared += row[4]
            percentage_reference = format(row[3] / reference_tokens_count,
                                          '0.3%')
            percentage_compared = format(row[4] / compared_tokens_count,
                                         '0.3%')
            running_percentage_reference = format(running_count_reference /
                                                  reference_tokens_count,
                                                  '0.3%')
            running_percentage_compared = format(running_count_compared /
                                                 compared_tokens_count, '0.3%')
            errors_grouped_by_tag_with_running_counts_and_percentage.append(
                tuple(row) + (percentage_reference, percentage_compared,
                              running_percentage_reference,
                              running_percentage_compared))

        # ⇒ ambiguous attr combinations
        with open('errors-grouped-by-tag-{}.html'.format(attribute),
                  'w') as summary:
            print(html_writer.header(
                'Tagging errors grouped by tags',
                argv=self.args['argv']), file=summary)

            for line in html_writer.simple_table(
                    errors_grouped_by_tag_with_running_counts_and_percentage, [
                        'Expected', 'Got', 'Words', 'Reference count',
                        'Compared', 'Percentage of errors reference',
                        'Compared', 'Running percentage reference',
                        'Compared']):
                print(line, file=summary)

            print(html_writer.after_content, file=summary)

    def save_errors_by_tag_difference(self, unsorted_errors, attribute):
        """
        První úroveň slovníku: rozdílné atributy (seřazené, např. kx)
        Druhá úroveň slovníku: první značka, mezera, druhá značka anebo prostě
                               tuple
        Obsah: zase slova a počty…
        """
        ab_diff_separated = {}  # slovník, kde klíče jsou dvojice frozensetů
        for row in unsorted_errors:
            expected, got = self._asymmetric_tag_difference(row)

            # pokud mám zgroupovaný chyby do skupin, tak to strčit do skupiny,
            # jinak nechat zvlášť

            group = ab_diff_separated.setdefault((expected, got), [])
            group.append(row)

        clustered = set()

        grouped_errors = OrderedDict()
        for group_name, attrs in ERROR_GROUPS.items():
            # přidání do clusteru všeho se nepočítá jako clusterování
            if attrs == [({}, {})]:
                for (expected, got), words in ab_diff_separated.items():
                    group = grouped_errors.setdefault(group_name, {})
                    group[(expected, got)] = words
                continue

            # ostatní clustery jo
            for (expected, got), words in ab_diff_separated.items():
                for expected_for_grouping, got_for_grouping in attrs:
                    if (self._all_attrs_match(expected_for_grouping, expected)
                            and self._all_attrs_match(got_for_grouping, got)):
                        group = grouped_errors.setdefault(group_name, {})
                        group[(expected, got)] = words
                        clustered.add((expected, got))
                        break

        grouped_errors['unclustered'] = dict(
            (expected_got, words) for expected_got, words
             in ab_diff_separated.items() if expected_got not in clustered)

        # součty chyb pro clustery
        reference_counts = {}
        compared_counts = {}

        # tady ty clusterovaný skupiny chyb vezmu a udělám z nich ty klasický
        # tabulky (jak byla dřív jenom jedna velká bez clusterování, tak teď
        # jich je několik za sebou)
        grouped_errors_sorted = OrderedDict()
        for group_name, attrs in grouped_errors.items():
            grouped_errors_sorted[group_name] = \
                self._sorted_by_group_frequency(attrs)
            words = attrs.values()
            reference_counts[group_name] = sum(
                sum(word.reference_count for word in words)
                for words in attrs.values())
            compared_counts[group_name] = sum(
                sum(word.compared_count for word in words)
                for words in attrs.values())

        reference_tokens_total = self.summary['reference']['whole-tag']['total']
        compared_tokens_total = self.summary['compared']['whole-tag']['total']
        alias = self.specification.options.get('id')
        # WISH: předávat fold jako parametr
        fold = PosixPath().resolve().name

        # NOTE: dřív jsem to zamejšlel dělat samostatně podle atributů
        #       (včetně -indirect)
        with open('clustered-errors-overview.html', 'w') as overview:
            print(html_writer.header(
                '{} ({}) – clustered errors overview'.format(alias, fold),
                argv=self.args['argv']), file=overview)

            print('<pre>{0}</pre>'.format(self.specification.long_format()),
                  file=overview)

            for line in self.overview_of_clusters(grouped_errors_sorted,
                                                  reference_counts,
                                                  compared_counts,
                                                  reference_tokens_total,
                                                  compared_tokens_total):
                print(line, file=overview)
            print('</table>', file=overview)

        # WISH: přehled značek a slov, kde NEjsou chyby
        with open('clustered-errors-listing.html', 'w') as summary:
            print(html_writer.header(
                '{} ({}) – clustered errors listing'.format(alias, fold),
                argv=self.args['argv']), file=summary)

            print('<pre>{0}</pre>'.format(self.specification.long_format()),
                  file=summary)

            for line in self.overview_of_clusters(grouped_errors_sorted,
                                                  reference_counts,
                                                  compared_counts,
                                                  reference_tokens_total,
                                                  compared_tokens_total):
                print(line, file=summary)
            print('</table>', file=summary)

            for group_name, attrs in grouped_errors_sorted.items():
                print('<h2 id="{0}">{0}</h2>'.format(group_name), file=summary)

                for line in html_writer.simple_table(
                        attrs, [
                            'Attrs', 'Number of words', 'Number of errors (ref, comp, diff)',
                            '% of all tokens (gain ref, comp, diff)', 'Words']):
                    print(line, file=summary)

            print(html_writer.after_content, file=summary)

    def overview_of_clusters(self, grouped_errors_sorted, reference_counts,
                             compared_counts, reference_tokens_total,
                             compared_tokens_total):
        yield '<table class="tagging-errors-overview">'
        overview = []
        overview.append('cluster reference compared diff reference compared diff'.split())
        for group_name in grouped_errors_sorted:
            overview.append((
                '<a href="{1}#{0}">{0}</a>'.format(
                    group_name, 'clustered-errors-listing.html'),
                reference_counts[group_name] / reference_tokens_total,
                compared_counts[group_name] / compared_tokens_total,
                compared_counts[group_name] / compared_tokens_total -
                reference_counts[group_name] / reference_tokens_total,
                reference_counts[group_name], compared_counts[group_name],
                compared_counts[group_name] - reference_counts[group_name]))

        overview.append(('tokens', '100%', '100%', 0,
                         reference_tokens_total, compared_tokens_total, 0))

        yield from html_writer.simple_table(overview, header_lines=1,
                                            enclose_in_tags=False)
                                            # footer=True)
        yield '</table>'


    def _all_attrs_match(self, attrs_to_match, tested_values):
        # převod z frozenset, kde to je jako 'c4', na 'c': '4'
        tested_values = dict(attr_val for attr_val in tested_values)

        for attr, expected_value in attrs_to_match.items():
            tested_value = tested_values.get(attr)
            if expected_value is None:
                if tested_value is not None:
                    return False
            elif tested_value is None:
                return False
            # REGEXES 4 LIFE
            elif not re.match(expected_value, tested_value):
                return False
        return True

    def _asymmetric_tag_difference(self, word_tags_error_count) -> frozenset:
        row = word_tags_error_count

        expected_attrs_values = frozenset(pairs(row.expected_tag))
        given_attrs_values = frozenset(pairs(row.given_tag))
        # remove common attrs-values
        return (expected_attrs_values - given_attrs_values,
                given_attrs_values - expected_attrs_values)

    # https://docs.python.org/3/library/typing.html
    # https://www.python.org/dev/peps/pep-3107/
    # >>> _symmetric_tag_difference.__annotations__
    # {'return': <class 'frozenset'>}
    # https://code.tutsplus.com/tutorials/python-3-function-annotations--cms-25689
    def _symmetric_tag_difference(self, word_tags_error_count) -> frozenset:
        row = word_tags_error_count

        # unsorted_errors.append(Row(
        #     expected_tag,  # Cheap Trick – If You Want My Love
        #     given_tag,  # zněj trochu jako Beatles
        #     word,
        #     reference_and_compared_counts.get('reference', 0),
        #     reference_and_compared_counts.get('compared', 0),
        # ))

        # Row = namedtuple('Row', ['expected_tag', 'given_tag', 'word',
        #                          'reference_count', 'compared_count'])

        expected_attrs_values = frozenset(pairs(row.expected_tag))
        given_attrs_values = frozenset(pairs(row.given_tag))
        return expected_attrs_values.symmetric_difference(
            given_attrs_values)

    def _sorted_by_group_frequency(self, grouped_by_attr_difference):
        sorted_by_group_frequency = list(sorted(
            grouped_by_attr_difference.items(), key=lambda group:
            # TODO: hybridní řazení (podle maxima z obou stran)
            sum(word.reference_count for word in group[1]), reverse=True))

        reference_tokens_total = self.summary['reference']['whole-tag']['total']
        compared_tokens_total = self.summary['compared']['whole-tag']['total']

        # tohle vytvoří tabulku se sloupci „(symetrický) rozdíl mezi značkami“,
        # počet slov, počet chyb (počet všech chybných výskytů slov), procentu-
        # ální význam té chyby na počtu všech tokenů („kdyby nebyla, tak je
        # přesnost o tolik víc“) a nakonec slova seřazený sestupně podle počtu
        sorted_by_group_frequency_ = []
        for (expected, got), words in sorted_by_group_frequency:
            reference_errors_count = sum(word.reference_count for word in words)
            compared_errors_count = sum(word.compared_count for word in words)

            sorted_by_group_frequency_.append((
                ''.join(sorted(expected)) + ' ' + ''.join(sorted(got)),
                len(words),
                '{}<br>{}<br>{}'.format(reference_errors_count,
                                        compared_errors_count,
                                        compared_errors_count -
                                        reference_errors_count),
                '{0:0.3%}<br>{1:0.3%}<br>{2:0.3%}'.format(
                    reference_errors_count / reference_tokens_total,
                    compared_errors_count / compared_tokens_total,
                    compared_errors_count / compared_tokens_total -
                    reference_errors_count / reference_tokens_total),
                # WISH: radši tabulku, co by šla krátit, jako jsem měl dřív?
                ' '.join('{} ({}/{})'.format(_highlight_higher_and_lower(
                        word), word.reference_count, word.compared_count)
                         for word in sorted(words, key=lambda word:
                                            word.reference_count,
                                            reverse=True))))

        return sorted_by_group_frequency_


def _highlight_higher_and_lower(word):
    worse = word.compared_count > word.reference_count
    better = word.compared_count < word.reference_count
    return '<span class="highest">{}</span>'.format(word.word) if worse else \
    '<span class="lowest">{}</span>'.format(word.word) if better else word.word


if __name__ == '__main__':
    # NOTE: tohle skoro zavání Javou
    primary_evaluation = CompareTaggedCorpusAgainstGolden(sys.argv)
    primary_evaluation.compare_corpus_against_reference_corpus()
