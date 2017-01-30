#!/usr/bin/env python3
import doctest
import sys

import rftagger
from tagsetbench import ShellPath, read_args


def annotate():
    args = {
        'corpus': ShellPath(),
        'model': ShellPath(),
        'tagged-corpus': ShellPath(),
        'rftagger-try-lowercase': False,

        'tagger': rftagger.NAME,
        'tagset': 'cz_attributive_brno',  # rftagger.annotate uses this
    }

    args = read_args(sys.argv, args)

    # TODO: radši pouštět doctest explicitně třeba jako ./annotate.py doctest
    if not args['model'].name:
        doctest.testmod(optionflags=doctest.NORMALIZE_WHITESPACE)
        return

    if args['tagger'] == rftagger.NAME:
        rftagger.annotate(args)
    else:
        raise NotImplementedError('Tagger "{}" not supported.'.format(
            args['tagger']))


if __name__ == '__main__':
    annotate()
