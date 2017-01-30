#!/usr/bin/env python3
from collections import defaultdict
import doctest
import json
from pathlib import PosixPath
import re
import sys

import html_writer
from tagsetbench import read_args, serialize_input_params
from vertical import read_vertical


# TODO: myslím si, že bych tu měl mít přepínač, aby se koukalo do MWE
# TODO: a hlavně do jakého druhu

class Lexicon:
    def __init__(self, argv):
        args = {
            'corpus': PosixPath(),
            'exclude-tag': '',  # regex, třeba '^k[125?]'
            'case-sensitive': True,
            'lexicon': PosixPath(),
            'untagged-report': PosixPath(),
            'ambiguity-report': PosixPath(),
        }
        self.args = read_args(argv, args)
        self.args['self'] = PosixPath(__file__).resolve()

    def generate_statistics(self):
        if not self.args['corpus'].name:
            doctest.testmod(optionflags=doctest.NORMALIZE_WHITESPACE)
            return

        if self.args['exclude-tag']:
            exclude_tag = re.compile(self.args['exclude-tag'])
        else:
            exclude_tag = None

        words = {}
        untagged = defaultdict(int)
        with self.args['corpus'].open() as f:
            # TODO: Musí se naučit zpracovávat všechny značky nejlíp asi
            # dynamickou referencí na funkci, která je bude načítat/zpracovávat
            # (anebo vlastně ani nebude muset, je to zbytečný zdržování!).
            for xml_tag, token in read_vertical(f):
                if token:
                    if exclude_tag and exclude_tag.match(token.tag):
                        continue

                    if not self.args['case-sensitive']:
                        token['word'] = token['word'].upper()

                    tag_counts = words.setdefault(token['word'],
                                                  defaultdict(int))
                    tag_counts[token.tag] += 1
                    if token.tag == 'k?':
                        untagged[token['word']] += 1

        input_params = json.dumps(
            serialize_input_params(self.args), sort_keys=True, indent=4)

        if self.args['lexicon'].name:
            with self.args['lexicon'].open('w') as output:
                json.dump(words, output, indent=4, sort_keys=True,
                          ensure_ascii=False)

        if self.args['untagged-report'].name:
            with self.args['untagged-report'].open('w') as output:
                print(html_writer.header('Untagged',
                                         input_params), file=output)
                for line in self.print_untagged(untagged):
                    print(line, file=output)
                print(html_writer.after_content, file=output)

        if self.args['ambiguity-report'].name:
            with self.args['ambiguity-report'].open('w') as output:
                print(html_writer.header('Ambiguous',
                                         input_params), file=output)
                for line in self.print_ambiguity(words):
                    print(line, file=output)
                print(html_writer.after_content, file=output)

    def print_ambiguity(self, words):
        yield '<table>'
        yield ('<tr><th colspan="2">Ambiguity in tags (case-{}sensitive)'
               '</th></tr>'.format('' if self.args['case-sensitive'] else
                                   'in'))
        last_count = None
        subtotal = 0
        # ty pojmy by měly znamenat to samý, odlišuju je po svém
        running_total = 0

        for word, tag_counts in sorted(
                words.items(), key=lambda w_tc:
                (len(w_tc[1]), sum(w_tc[1].values())), reverse=True):
            if last_count is None:
                last_count = len(tag_counts)
            elif len(tag_counts) != last_count:
                running_total += subtotal
                yield ('<tr><th>Subtotal: {}</th><th>Running total: {}'
                       '</th></tr>'.format(subtotal, running_total))
                subtotal = 0
            yield from self.print_ambiguity_details(word, tag_counts)
            subtotal += 1
            last_count = len(tag_counts)
        running_total += subtotal
        yield ('<tr><th>Subtotal: {}</th><th>Running total: {}</th>'
               '</tr>'.format(subtotal, running_total))
        yield '</table>'

    def print_ambiguity_details(self, word, tag_counts):
        first = True
        for tag, count in sorted(tag_counts.items(),
                                 key=lambda item: item[1], reverse=True):
            if first:
                yield ('<tr><th rowspan="{}">{}</th><td>{} ({})</td>'
                       '</tr>'.format(len(tag_counts), word, tag, count))
                first = False
            else:
                yield ('<tr><td>{} ({})</td></tr>'.format(tag, count))

    def print_untagged(self, untagged):
        yield '<table>'
        yield ('<tr><th colspan="2">Untagged ({}, {})</th></tr>'.format(
            len(untagged), sum(untagged.values())))
        for word, count in sorted(untagged.items(), key=lambda item: item[1],
                                  reverse=True):
            yield ('<tr><th>{}</th><td>{}</td></tr>'.format(word, count))
        yield '</table>'


if __name__ == '__main__':
    lexicon = Lexicon(sys.argv)
    lexicon.generate_statistics()
