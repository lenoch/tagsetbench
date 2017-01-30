from subprocess import PIPE, Popen

import cz_brno_attributive
from symbols import Token, pairs
from vertical import read_sentences

# TODO: rft-print by se mohl někdy hodit na výpis zajímavých informací z modelu
NAME = 'rftagger'


def complete_tag(token):
    try:
        kind = token['k']
    except KeyError:
        # log.warning('\n'.join(token.plain_vertical()))
        kind = token['k'] = '?'
    attributes = cz_brno_attributive.ATTRIBUTES.get(kind, '')
    for attr in attributes:
        if attr not in token:
            token[attr] = '?'


def annotate(args):
    """
    Baby-sit RFTagger’s rft-annotate tool. When fed with vertical text followed
    by a blank line, it outputs a tagged sentence.

    rft-annotate parfile [infile [outfile]]

    -t v beam threshold
    -u   no normalization of probabilities
    -s   consider the lower-case version of sentence-initial words
    -hh  hyphenation heuristic: lookup "prone" if "error-prone" is not in the
         lexicon
    -q   quiet mode
    -v   verbose mode
    -h   this message

    NOTE: rft-annotate outputs the sequential number of a sentence (starting
          with 0) to stderr; however, it doesn't add a trailing \n so readline
          cannot be used. Using stderr is thus deadlock-prone unless going much
          higher in complexity: http://stackoverflow.com/questions/375427/
          non-blocking-read-on-a-subprocess-pipe-in-python or
          http://stefaanlippens.net/python-asynchronous-subprocess-pipe-reading

    NOTE: Aha, rft-annotate displays progress this way so it is better left to
          output the sentence numbers to make the process more interactive.
    """
    if args['tagset'] == 'cz_attributive_brno':
        parse_word_tag = parse_word_tag_brno

    command = ['rft-annotate']
    if args['rftagger-try-lowercase']:
        command += ['-s']
    command += [str(args['model'])]

    with Popen(command,
               universal_newlines=True, stdin=PIPE, stdout=PIPE, bufsize=0
               ) as proc, args['corpus'].open() as corpus, args[
                'tagged-corpus'].open('w') as output:
        for sentence in read_sentences(corpus):
            for token in sentence.tokens:
                if token.use_internal_tokens:
                    for internal_token in token.tokens:
                        print(internal_token['word'], file=proc.stdin)
                else:
                    print(token['word'], file=proc.stdin)

            print(file=proc.stdin)  # Ask RFTagger to print the sentence.

            print(sentence.opening_tag, file=output)
            for i, token in enumerate(sentence.tokens):
                if token.use_internal_tokens:
                    for j, internal_token in enumerate(token.tokens):
                        line = proc.stdout.readline()
                        word, tag = parse_word_tag(line)
                        internal_token.new_tag = tag
                else:
                    line = proc.stdout.readline()
                    word, tag = parse_word_tag(line)
                    token.new_tag = tag
                for line in token.lines():
                    print(line, file=output)
            print(sentence.closing_tag, file=output)

            # RFTagger outputs a blank line after a tagged sentence.
            blank = proc.stdout.readline()
            if blank.strip():  # Check that the above claim is true.
                raise ValueError('RFTagger printed a non-blank line after '
                                 'a tagged sentence: "%s"' % blank)


def parse_word_tag_brno(line):
    """
    Parse the line and return the word and the tag. RFTagger doesn't support
    lemmata, as of Feb 2016.

    Trailing \n is stripped first so tags with a non-empty value at the end
    (commonly kIx. — ending punctuation) don’t result in an extra blank line.

    The tag’s attributes, separated by full stops, are joined together,
    skipping empty ones except the kind (k). Empty attributes have “?” as
    a value. They are often at the end of the tag (e.g. ~, not even used yet).

    Note that this function is tailored to the Brno’s attributive tagset.
    """
    word, tag = line.strip().split('\t')
    attrs = tag.split('.')

    tag = ''.join(attr for attr in attrs if attr[1] != '?' or attr[0] == 'k')

    if 'FULLSTOP' in tag:
        tag = tag.replace('FULLSTOP', '.')

    return word, tag


def convert_tag(token=None, tag=None):
    if tag:
        token = Token(tag=tag)

    complete_tag(token)

    # Replace a full stop (.), which serves as a delimiter, with something
    # less ambiguous.
    tag = token.tag
    if '.' in tag:
        attrs = (attr.replace('.', 'FULLSTOP') for attr in pairs(tag))
    else:
        attrs = pairs(tag)

    return '.'.join(attrs)


def token_lines(token):
    if token.use_internal_tokens:
        for internal_token in token.tokens:
            yield '\t'.join((internal_token['word'],
                             convert_tag(internal_token)))
    else:
        yield '\t'.join((token['word'], convert_tag(token)))


# from rftagger import convert_tag
# with open('../značky.json') as f:
#     for značka in f:
#         print(convert_tag(tag=značka.strip()))
