#!/usr/bin/env python3
import doctest
from subprocess import run
import sys

import rftagger
from tagsetbench import ShellPath, read_args


def create_model():
    args = {
        'training-corpus': ShellPath(),
        'rftagger-lexicon': ShellPath(),
        'rftagger-possible-unknown-tags': ShellPath(),
        # 'temporary-corpus': ShellPath(),
        # mám symlinky v pracovním adresáři
        'rftagger-wordclass-automaton': ShellPath(
            'RFTagger/wordclass/wordclass.txt'),

        'tagger': rftagger.NAME,
        # DONE:
        # Marek používal kontext -c 8, výchozí je -c 2 a -c 20 už nepomohl, ale
        # když si to pěkně zautomatizuju (./configure i make v cyklu, pokaždé
        # buď získávat výsledky anebo je ukládat mimo pracování adresář anebo
        # to dávat do různých pracovních adresářů), můžu přijít na nejvhodnější
        'rftagger-context-length': 5,

        'rftagger-verbose-training-log': False,

        'model': ShellPath(),
        'training-log': ShellPath(),
    }

    args = read_args(sys.argv, args)

    # TODO: spíš vyhodit výjimku (a doctest dělat na požádání, explicitně)
    if not args['training-corpus'].name and not args['model'].name:
        doctest.testmod(optionflags=doctest.NORMALIZE_WHITESPACE)
        return

    if args['tagger'] == rftagger.NAME:
        cmd = [
            'rft-train',  # PATH=/RFTagger/is/here:$PATH
            args['training-corpus'],  # corpus
            args['rftagger-wordclass-automaton'],
            args['model'],  # parfile
            # "The n preceding tags are used as context (default 2)."
            '-c', str(args['rftagger-context-length']),

            # TODO: args['rftagger-verbose-training-log']
            # "The verbose mode is turned on."
            '-v',  # Vypadá to, že to s -vv (very verbose mode) padá.
        ]

        if args['rftagger-lexicon'].is_file():
            # "Additional lexicon entries are supplied in file f."
            cmd += ['-l', args['rftagger-lexicon']]

            # TODO: pro tu srandu a porovnání, co takhle opravdu zkusit rozdíl
            # v úspěšnosti mezi čistým modelem a modelem rozšířeným o lexikon
            # opět jen z trénovacího korpusu? Podle mě by to mělo dopadnout
            # skoro stejně.

        if args['rftagger-possible-unknown-tags'].is_file():
            # "The possible POS tags of unknown words are restricted to those
            # listed in file f."
            # Tagy otevřených slovních kategorií (omezení pouze na ně)
            # pomocí -o, ale nejdřív bych tam musel dát i kA.
            cmd += ['-o', args['rftagger-possible-unknown-tags']]
            # Slovník, který nejspíš omezí možnost (pozitivního) hádání (aspoň
            # něco místo k?), protože nemám zatím jiný zdroj, ale taky
            # (negativního) hádání (k1 místo k5) se zpřístupní pomocí -o
            # slovnik.vert (tagy a lemmata přehozeně)

        cmd = [str(arg) for arg in cmd]

        # TODO: vypisuje na stderr chyby do logu, takže si jich můžu tady
        # všimnout, na to možná bude lepší vyčítat stderr ve smyčce
        with args['training-log'].open('w') as stderr:
            completed_process = run(cmd, stderr=stderr, check=True,
                                    universal_newlines=True)
            print(completed_process)

    else:
        raise NotImplementedError('Tagger "{}" not supported.'.format(
            args['tagger']))


if __name__ == '__main__':
    create_model()
