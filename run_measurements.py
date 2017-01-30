#!/usr/bin/env python3
import subprocess


def k6k9():
    words = """
        již, prostě, právě, potom, také, Ještě, jasně, jistě, jen, zvláště,
        Právě, Jenom, bohužel, Bohužel, Již, Už, až, především, většinou,
        jenom, Víceméně, Především, ještě, už""".split(',')
    words = frozenset(word.strip().lower() for word in words)
    for word in words:
        subprocess.run(['xdg-open',
                        'enqueue:{0}-k6eAd1-k9.sh?aurora'.format(word)])
        subprocess.run(['xdg-open',
                        'enqueue:{0}-k9-k6eAd1.sh?aurora'.format(word)])


def context_length():
    for length in range(13, 31):
        subprocess.run(['xdg-open',
                        'enqueue:context-length-{0}.sh?aurora'.format(length)])


if __name__ == '__main__':
    context_length()
