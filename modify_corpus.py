#!/usr/bin/env python3
from importlib import import_module
from pathlib import PosixPath
import sys

from log import log
import models
from tagsetbench import read_args
from vertical import parse_token_with_two_tags, read_sentences


PARAMETERS = {
    'input-corpus': PosixPath(),

    'complex-modification': '',
    'two-tags': False,

    'output-corpus': PosixPath(),
}


BOOTSTRAP_MODIFICATIONS = """
    MODIFIER
      alias=bootstrap.punctuation
      silent=yes
      MATCH
        k=\?
        word=[-,.():?"!\;\/]|...
      SET
        k=I
    MODIFIER
      alias=bootstrap.cardinal_number
      silent=yes
      MATCH
        k=\?
        word=[0-9 ]+
      SET
        k=4
        x=C
"""


class CorpusModifier:
    def __init__(self, argv):
        self.args = read_args(argv, PARAMETERS)

        parsed = models.parse(
            self.args['complex-modification'])
        # WISH: jsou stejný, ale stejně bych radši viděl .modifications
        # WISH: asi bych měl ModificationParams přejmenovat
        modifications = parsed.sides[0].training_modifications
        options = parsed.sides[0].options  # TODO: bootstrap řešit už v configure

        log.info('Processing %s and saving to %s', self.args['input-corpus'],
                 self.args['output-corpus'])
        # log.info('Parse expected_tag + assigned_tag: %s',
        #          self.args['two-tags'])

        if not modifications or modifications[0].name != 'rftagger-preprocess':
            if options.get('bootstrap', 'yes').lower() not in (
                    '', 'no', 'false'):
                bootstrap = models.parse(
                    BOOTSTRAP_MODIFICATIONS).sides[0].training_modifications
                modifications = bootstrap + modifications
                parsed.sides[0].training_modifications = modifications

         # log.info('Complex options:\n%s', parsed.long_format())

        self.modifiers = []
        for modifier in modifications:
            name = modifier.name.replace('-', '_')
            name_parts = name.split('.', 2)
            if len(name_parts) == 1:
                module_name = function_name = name
            else:
                module_name, function_name = name_parts

            modifier_module = import_module('modifier.{}'.format(
                module_name))
            modifier_class = getattr(modifier_module, function_name)
            self.modifiers.append(modifier_class(modifier))

        self.token_parser = None
        if self.args['two-tags']:
            self.token_parser = parse_token_with_two_tags

    def modify_corpus(self):
        with self.args['input-corpus'].open() as input_file, self.args[
                'output-corpus'].open('w') as output_file:
            for sentence in read_sentences(
                    input_file, self.token_parser):

                for modifier in self.modifiers:
                    modifier(sentence)

                for line in sentence.lines():
                    print(line, file=output_file)

        for modifier in self.modifiers:
            summary = [part.strip() for part in modifier.model.encode()][1:]
            summary += ['HITS', str(modifier.tokens_modified)]
            log.info('%s/%s  %s', PosixPath().resolve().name,
                     self.args['input-corpus'], '  '.join(summary))


if __name__ == '__main__':
    corpus_modifier = CorpusModifier(sys.argv)
    corpus_modifier.modify_corpus()
