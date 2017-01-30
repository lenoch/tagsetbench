#!/usr/bin/env python3
import doctest
import sys

from rftagger import complete_tag
from symbols import pairs
from tagsetbench import read_args
from vertical import read_vertical


def create_lexicon():
    args = {
        'input': '',
        'output': '',
    }
    args = read_args(sys.argv, args)

    if not args['input'] or not args['output']:
        doctest.testmod(optionflags=doctest.NORMALIZE_WHITESPACE)
        return

    entries = set()  # TODO: proč to znovu řadím?!
    with open(args['input']) as f:
        for xml_tag, token in read_vertical(f):
            if token:
                # Bere to token a ne jen tag, takže nemůžu levně naházet
                # trojice (s token.original_tag) do množiny a pak každou
                # unikátní trojici vypsat po seřazení. Co už.
                complete_tag(token)
                entries.add((token['word'], '.'.join(pairs(token.tag)),
                             token['lemma']))

    with open(args['output'], 'w') as output:
        for entry in sorted(entries):
            print(*entry, sep='\t', file=output)


if __name__ == '__main__':
    create_lexicon()
