#!/usr/bin/env python3
import doctest
from itertools import product
import subprocess
import sys

import rftagger
from tagsetbench import ShellPath, read_args


def main():
    if len(sys.argv) > 1:
        extract_data()
    else:
        doctest.testmod(verbose=True)
    # expand_lexicon()


def word_combinations(alphabet, min_length=1, max_length=20):
    for length in range(min_length, max_length + 1):
        yield from product(alphabet, repeat=length)


def pairs(lemma_tag):
    units = iter(lemma_tag)
    for unit in units:
        yield (unit, next(units))


def expand_lexicon():
    args = {
        'db': '',
        'input': '',
        'output': '',
        'majka': '',
    }
    args = read_args(sys.argv, args)

    proc = subprocess.Popen([args['majka'], '-f', args['db'], '-p'],
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL,
                            bufsize=0)

    last_word = ''
    with open(args['input']) as f:
        with open(args['output'], 'w') as output:
            for line in f:
                word = line.split('\t')[0]
                if last_word == word:
                    continue
                last_word = word
                proc.stdin.write((word + '\n').encode('UTF-8'))
                # TODO: anebo by šlo nějak print?

                line = proc.stdout.readline().decode('UTF-8').strip()
                majka_word, *lemmas_tags = line.split(':')
                for lemma, tag in pairs(lemmas_tags):
                    print(majka_word, lemma, tag, sep='\t', file=output)
                # if not lemmas_tags:
                #     print(majka_word, majka_word, 'k?', sep='\t',
                #           file=output)

    proc.stdin.close()
    # aby se program čistě ukončil a nebylo z něj ani chvilku zombie
    proc.wait()


def extract_data():
    args = {
        'dictionary': ShellPath(),

        # 'vertical': ShellPath(),
        'rftagger-lexicon': ShellPath(),
    }

    args = read_args(sys.argv, args)

    # NOTE: use PATH=/path/to/majka/:$PATH to point to the binary
    proc = subprocess.Popen(['majka', '-f', str(args['dictionary']), '-all'],
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL,
                            bufsize=0)

    skipped_prefixes = tuple(ord(char) for char in '!^')

    with args['rftagger-lexicon'].open('w') as rftagger_lexicon:
        for line in proc.stdout:
            if line[0] in skipped_prefixes:
                pass  # prefixes are stored in a majka db like "!česko-:1"
                # ^absolutistické  k2.eA.gF.nP.c1.d1.z?.w?.~?  ^absolutistický
                # (words accepting negation?)
            else:
                line = line.decode('latin2')
                word, lemma_recipe, tag = line.split(':', 3)
                lemma = create_lemma(word, lemma_recipe)
                rftagger_tag = rftagger.convert_tag(tag=tag.strip())
                print('\t'.join((word, rftagger_tag, lemma)),
                      file=rftagger_lexicon)


def create_lemma(word, lemma_recipe):
    """
    >>> create_lemma('pablbové', 'CDec')
    'blbec'
    """
    delete_at_start, replacement_prefix = parse_replacement(lemma_recipe)
    delete_at_end, replacement_suffix = parse_replacement(lemma_recipe[
        1 + len(replacement_prefix):])
    stem = word[delete_at_start:len(word)-delete_at_end]
    return replacement_prefix + stem + replacement_suffix


def parse_replacement(lemma_recipe):
    deletion_length = ord(lemma_recipe[0]) - ord('A')
    if deletion_length in range(0, 26):
        return deletion_length, consume_replacement(lemma_recipe[1:])
    else:
        raise ValueError('Invalid deletion length. Expected A-Z (0-26), '
                         'got {} ({})'.format(lemma_recipe[0],
                                              deletion_length))


def consume_replacement(lemma_recipe):
    for offset, char in enumerate(lemma_recipe):
        if ord(char) - ord('A') in range(0, 26):  # found deletion length mark
            return lemma_recipe[:offset]
    return lemma_recipe


if __name__ == '__main__':
    main()
