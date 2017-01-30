#!/usr/bin/env python3
from collections import OrderedDict
import json
from pathlib import PosixPath
import sys

from log import log
from tagsetbench import read_args


def partition_corpus():
    args = {
        'preprocessed-corpus': PosixPath(),
        'sentence-boundaries': PosixPath(),

        'portion': [''],  # from-to endpoints (separated by -)

        'partitioned-corpus': PosixPath(),
    }

    args = read_args(sys.argv, args)

    with args['sentence-boundaries'].open() as f:
        sentence_boundaries = json.load(f, object_pairs_hook=OrderedDict)
    # log.info(type(sentence_boundaries))

    partitions = [part.split('-') for part in args['portion']]

    # místa v procentech, odkud nebo pokud se bude dělit korpus
    # positions = set()
    # for start, stop in divisions:
    #     positions.update((start, stop))
    # positions = list(sorted(float(pos) / 100 for pos in positions))

    sentence_count = len(sentence_boundaries)
    last_sentence = sentence_boundaries[str(sentence_count)]
    total_line_count = last_sentence['starting-line'] + 2 + last_sentence['lines']
    total_token_count = last_sentence['total-tokens']

    log.info('Line count: %s\nToken count: %s\nSentence count: %s',
             total_line_count, total_token_count, sentence_count)

    threshold_token_counts = {}
    for start, stop in partitions:
        threshold_token_counts[start] = total_token_count * float(start) / 100
        threshold_token_counts[stop] = total_token_count * float(stop) / 100

    print(threshold_token_counts)

    # log.info('Splitting positions (relative to the size of the corpus): %s',
    #          positions)

    # počty tokenů, které odpovídají procentům „velikosti“ korpusu (velikost
    # korpusu měřím podle počtu všech tokenů bez ohledu na strukturní značky)
    # absolute_positions = [float(part) / 100 * total_token_count for part in
    #                       divisions]
    # log.info('Splitting positions (after having reached/surpassed the '
    #          'following token counts): %s', absolute_positions)

    thresholds = list(sorted(threshold_token_counts.items(),
                             key=lambda percent_threshold:
                                 float(percent_threshold[0])))
    print(thresholds)
    percent_to_line_number = {}

    # HACKed sentinel
    sentence_boundaries[str(sentence_count + 1)] = {
        'lines': 0,
        'starting-line': total_line_count,
        'total-tokens': total_token_count,
    }

    # for sentence_number, meta in sorted(sentence_boundaries.items(),
    #                                     key=lambda item: int(item[0])):
    for sentence_number, meta in sentence_boundaries.items():  # OrderedDict
        # čísla vět počítám lidsky, od jedničky

        preceding_token_count = 0  # previous_token_count?
        if int(sentence_number) > 1:
            preceding_token_count = sentence_boundaries[
                str(int(sentence_number) - 1)]['total-tokens']

        meta = sentence_boundaries[sentence_number] = {
            'lines': meta['lines'],
            'starting-line': meta['starting-line'],
            'preceding-token-count': preceding_token_count,
            # TODO: vyhodit, nějak?
            'total-tokens': meta['total-tokens'],
        }
        # TODO: když se budu nudit, tak preceding-token-count můžu generovat
        #       rovnou, bez té aktuální věty

        # relative_position = preceding_token_count / total_token_count
        if thresholds and preceding_token_count >= thresholds[0][1]:
            log.info('Passed {0:0.4}% tokens ({1:0.3%}) with preceding token '
                     'count {2} in sentence {3} ({4:0.3%})'.format(
                     float(thresholds[0][0]),
                     preceding_token_count / total_token_count,
                     preceding_token_count, sentence_number,
                     int(sentence_number) / sentence_count))
            p = thresholds.pop(0)
            percent_to_line_number[p[0]] = meta  # starting_line

    log.info('Percent to lines mapping: %s', percent_to_line_number)

    with args['preprocessed-corpus'].open() as f:
        corpus_lines = f.readlines()

    with args['partitioned-corpus'].open('w') as partitioned_corpus:
        for start, stop in partitions:  # skládám i dvě části jednoho korpusu
            meta_start = percent_to_line_number[start]
            meta_stop = percent_to_line_number[stop]
            first_line = meta_start['starting-line']
            # IDEA: prostě by se asi mělo končit začátkem následující věty,
            #       takže by měla bejt na konci ještě jedna plonková/sentinel
            last_line = meta_stop['starting-line']

            line_count = last_line - first_line
            token_count = (meta_stop['preceding-token-count'] -
                           meta_start['preceding-token-count'])

            log.info('{0}–{1} {2} first line: {3}, last line: {4}, '
                     'line count: {5} ({6:0.3%}), '
                     'token count: {7} ({8:0.3%})'.format(
                         start, stop,
                         args['partitioned-corpus'].name,
                         first_line, last_line,
                         line_count, line_count / total_line_count,
                         token_count, token_count / total_token_count))

            partitioned_corpus.writelines((corpus_lines[i] for i in
                                           range(first_line, last_line)))


if __name__ == '__main__':
    partition_corpus()
