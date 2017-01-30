from collections import OrderedDict
from datetime import datetime  # to parse source corpus timestamp
from functools import partial
from pathlib import PosixPath
import subprocess

from log import log
from tagsetbench import custom_repr


def fill_in_file_name(path_property):
    fixed_name_parts = path_property.__name__.split('_')
    return partial(path_property, fixed_name_parts=fixed_name_parts)


def join_name_parts(obj, fixed_name_parts, file_extension,
                    distinctive_name_parts=None):
    fixed_name_part = '-'.join(fixed_name_parts)
    if distinctive_name_parts is None:
        distinctive_name_parts = obj.name_parts[fixed_name_part]
    return PosixPath('-'.join(fixed_name_parts + distinctive_name_parts) +
                     file_extension)


# TODO: asi to budu moct vyhodit, jen to musím přestat využívat
#       v Comparison.shorten_file_names (stačí prostě „přestat krátit jména“)
# NOTE: tahle funkce je napsaná, aby šla pouštět s doctestem
def remove_common_name_parts(left, right):
    """
    Remove common traits from names of 'left' and 'right' instance, to
    shorten the resulting names. (Never include the distinguishing prefix.)

    >>> name_parts_a = ['desam', '0-25', 'original', 'context-3']
    >>> name_parts_b = ['desam', '0-25', 'conditional', 'context-4']
    >>> remove_common_name_parts(name_parts_a, name_parts_b)
    >>> name_parts_a
    ['original', 'context-3']
    >>> name_parts_b
    ['conditional', 'context-4']
    """
    filtered_left = []
    filtered_right = []
    for left_part, right_part in zip(left, right):
        if left_part != right_part:
            filtered_left.append(left_part)
            filtered_right.append(right_part)
    left.clear()
    right.clear()
    left.extend(filtered_left)
    right.extend(filtered_right)


@custom_repr
class SourceCorpus:
    CUSTOM_REPR_FIELDS = ('dummy', 'source_path', 'basename',
                          'preprocessed_path', 'size', 'datetime',
                          'git_commit')

    def __init__(self, path, sentence_boundaries_path, dummy=False):
        self.basename = PosixPath(path).name.replace(
            'preprocessed-', '').replace(
            '.vert', '')

        self.dummy = dummy  # external results are used

        if sentence_boundaries_path:
            self.source_path = None
            self.preprocessed_path = PosixPath(path)
            self.sentence_boundaries_path = PosixPath(sentence_boundaries_path)
        else:
            self.source_path = PosixPath(path)
            self.preprocessed_path = PosixPath(
                'preprocessed-' + self.basename + '.vert')
            self.sentence_boundaries_path = PosixPath(
                'sentence-boundaries-' + self.basename + '.json')

        self.size = None
        self.datetime = None
        self.git_commit = None

    @property
    def path(self):
        return self.source_path or self.preprocessed_path

    def gather_metadata(self):
        meta = self.path.stat()
        self.size = meta.st_size
        self.datetime = str(datetime.fromtimestamp(meta.st_mtime))

        self.git_commit = subprocess.run(
            'git show --oneline --no-patch'.split(), cwd=str(self.path.parent),
            stdout=subprocess.PIPE, universal_newlines=True).stdout.strip()


@custom_repr
class TestingPair:  # TODO: EvaluationPair (TrainingTestingPair)
    CUSTOM_REPR_FIELDS = ('training_corpus', 'testing_corpus')

    def __init__(self, training_corpus, testing_corpus):
        self.training_corpus = training_corpus
        self.testing_corpus = testing_corpus

        self.reference_partitions = []
        self.compared_partitions = []

    def set_options(self, reference_or_compared, options):
        destination = getattr(self, '{}_options'.format(reference_or_compared))
        destination.update(options)


@custom_repr
class DerivedCorpus:
    CUSTOM_REPR_FIELDS = ('parent_corpus', 'dummy', 'basename', 'role', 'path',
                          'partition')

    def __init__(self, parent_corpus, role, partition=None, name_parts=None):
        self.parent_corpus = parent_corpus
        self.dummy = parent_corpus.dummy
        self.role = role
        self.partition = partition or parent_corpus.partition

        self.basename = self.parent_corpus.basename
        self.name_parts = name_parts or self.create_name_parts()

        if self.role in ('training', 'testing'):
            self.lexicon = Lexicon(self)

    def create_name_parts(self):
        return {'partitioned-corpus': [self.basename, self.partition]}

    @property
    def path(self):
        return join_name_parts(self, [self.role, 'corpus'], '.vert')

    @property
    def dependencies(self):
        if self.role == 'partitioned':
            return [self.parent_corpus.preprocessed_path,
                    self.parent_corpus.sentence_boundaries_path]
        elif self.role == 'training':
            raise NotImplementedError('TODO')
        elif self.role == 'testing':
            raise NotImplementedError('TODO')


@custom_repr
class Lexicon:
    def __init__(self, corpus):
        self.corpus = corpus
        self.name_parts = corpus.name_parts

    @property
    def path(self):
        return join_name_parts(self, [self.corpus.role, 'lexicon'], '.json')

    @property
    def dependencies(self):
        return [self.corpus]


# TODO: jojo, in fact jde o TaggedCorpus :-)
@custom_repr
class Evaluation:
    """
    TODO: po každém rozdělení dvojice korpusů, co se upraví, natrénuje, označ-
          kuje, vyhodnotí a nakonec porovná s odpovídajícím rozdělením, co bylo
          taky upraveno, ale většinou jinak, anebo bylo z jiného, ale porovna-
          telného korpusu
    """
    CUSTOM_REPR_FIELDS = (
        'options',
        'training_corpus', 'testing_corpus',
        'partitioned_training_corpus',
        'partitioned_testing_corpus',
        )

    def __init__(self, partitioned_training_corpus, partitioned_testing_corpus,
                 meta, reference_or_compared):
        self.partitioned_training_corpus = partitioned_training_corpus
        self.partitioned_testing_corpus = partitioned_testing_corpus
        self.external_tagged_corpus = None
        self.external_training_lexicon = None
        self.meta = meta
        self.options = self.meta.options
        self.reference_or_compared = reference_or_compared
        self.makefile = None

        self.name_parts = self.create_name_parts()

        self.training_corpus = DerivedCorpus(self.partitioned_training_corpus,
                                             'training',
                                             name_parts=self.name_parts)
        self.testing_corpus = DerivedCorpus(self.partitioned_testing_corpus,
                                            'testing',
                                            name_parts=self.name_parts)

        # TODO: nějak hezčím způsobem
        for path in ('rftagger-possible-unknown-tags', 'rftagger-lexicon'):
            if path in self.options:
                self.options[path] = PosixPath(self.options[path])

    def create_name_parts(self):
        """
        TODO: zjednodušit, využít fixní názvy, aby se daly určit a na ničem
              nezávisely
        """
        # BYLO: Include distinctive features in names of intermediate files.
        return {
            'training-corpus': [self.reference_or_compared],
            'training-lexicon': [self.reference_or_compared],
            'preprocessed-for-training': [self.reference_or_compared],
            'trained-model': [self.reference_or_compared],
            'training-log': [self.reference_or_compared],
            'testing-corpus': [self.reference_or_compared],
            'testing-lexicon': [self.reference_or_compared],
            'tagged-corpus': [self.reference_or_compared],
        }

    # TODO: všechny tyhle hovadiny se daj taky vygenerovat
    @property
    @fill_in_file_name
    def preprocessed_for_training(self, fixed_name_parts=['magic']):
        # NOTE: bohužel se musí nejdřív vytvářet trénovací korpus kvůli
        #       lexikonu, nejde to sloučit do jednoho kroku
        return join_name_parts(self, fixed_name_parts, '.vert')

    @property
    @fill_in_file_name
    def trained_model(self, fixed_name_parts=['magic']):
        return join_name_parts(self, fixed_name_parts, '.bin')

    @property
    @fill_in_file_name
    def training_log(self, fixed_name_parts=['magic']):
        return join_name_parts(self, fixed_name_parts, '.log')

    @property
    @fill_in_file_name
    def tagged_corpus(self, fixed_name_parts=['magic']):
        return join_name_parts(self, fixed_name_parts, '.vert')

    # @property
    # def json_summary(self):
    #     return join_name_parts(self, ['evaluation', 'summary'], '.json')
    #
    # @property
    # def html_summary(self):
    #     return join_name_parts(self, ['evaluation', 'summary'], '.html')

    path = tagged_corpus  # json_summary


@custom_repr
class Comparison:  # porovnání vyhodnocení (compared evaluation)
    """
    TODO: jestli chci docstring, tak možná vyleze z překladu, protože jsem si
          ty dvě vysvětlivky dal do text.html#principy a budu se snažit říct,
          co je evaluation/comparison/measurement/experiment
    """
    CUSTOM_REPR_FIELDS = ('reference_corpus', 'compared_corpus')

    def __init__(self, reference_corpus, compared_corpus,
                 common_working_dir):
        self.reference_corpus = reference_corpus
        self.compared_corpus = compared_corpus
        self.common_working_dir = common_working_dir

        self.training_portion = \
            reference_corpus.partitioned_training_corpus.partition
        self.testing_portion = \
            compared_corpus.partitioned_testing_corpus.partition

        self.shorten_file_names()

        self.name_parts = self.create_name_parts()
        self.working_dir = self.create_dirname()

        self.makefile = None
        self.json_summary = self.create_summary_name('.json')
        self.html_summary = self.create_summary_name('.html')
        self.latex_summary = self.create_summary_name('.tex')

    def shorten_file_names(self):
        reference_name_parts = self.reference_corpus.name_parts
        compared_name_parts = self.compared_corpus.name_parts

        for key, name_parts in reference_name_parts.items():
            remove_common_name_parts(name_parts, compared_name_parts[key])

    # TODO: předělat to podobně jako v Evaluation
    def create_name_parts(self):
        # NOTE: hezký, ale třeba adresáře se liší jen parcelací korpusů
        # reference = self.reference_partition
        # compared = self.compared_partition
        # return [self.training_portion, self.testing_portion,
        #         reference.modification, compared.modification]
        return [self.training_portion, self.testing_portion]

    def create_dirname(self):
        return self.common_working_dir / '_'.join([self.training_portion,
                                                   self.testing_portion])

    def create_summary_name(self, extension):
        return PosixPath('comparison-summary-' + '_'.join(  # evaluation-
            [self.training_portion, self.testing_portion]) + extension)

    @property
    def distant_dependencies(self):  # partitioned corpora from common workdir
        """
        Return a list of objects this one depends on, to simplify Makefile
        creation.
        """
        return list(corpus for corpus in (
            self.reference_corpus.partitioned_training_corpus,
            self.reference_corpus.partitioned_testing_corpus,
            self.compared_corpus.partitioned_training_corpus,
            self.compared_corpus.partitioned_testing_corpus)
            if not corpus.dummy)

    @property
    def immediate_dependencies(self):  # evaluated partitions for comparison
        # WISH: a chci teda na něco slovník z testovacího korpusu?
        return [self.reference_corpus,
                self.reference_corpus.training_corpus.lexicon,
                self.compared_corpus,
                self.compared_corpus.training_corpus.lexicon,
                ]


#
# (TEST/EVALUATION/MEASUREMENT/MODIFICATION) SPECIFICATION
#


@custom_repr
class ModificationParams:  # parametry úprav, specifikace testu/vyhodnocení
    CUSTOM_REPR_FIELDS = ('sides',)
    def __init__(self, sides=None, options=None):
        self.sides = sides or []  # TODO: evaluations
        # WISH: 'id' doplňovat, pokud chybí (options.update)
        self.options = options or OrderedDict([
            ('id', '')],  # WISH: přejmenovat na "alias", protože rozhoduje i datum a čas
            # WISH: doplnit to datum a čas
        )

    def encode(self):
        commands = []
        for side in self.sides:
            commands += side.encode()
        # WISH: přejmenovat COMMON na COMPARE (ale vzadu to zůstat může)
        if self.options:
            commands += ['COMMON']
            for option, value in self.options.items():
                commands += ['  {}={}'.format(option, value)]
        return commands

    # WISH: klidně bych mohl vytvořit i __format__
    def long_format(self):
        return '\n'.join(self.encode())

    def short_format(self):
        return ';'.join(part.strip() for part in self.encode())


class ComparedSide:  # WISH: sloučit s Evaluation?
    def __init__(self):
        self.training_modifications = []
        self.testing_modifications = []
        self.options = OrderedDict()

    def encode(self):
        commands = ['EVALUATE']
        for option, value in self.options.items():
            commands += ['  {}={}'.format(option, value)]
        if self.training_modifications is self.testing_modifications:
            commands += ['  TRAINING_TESTING']
            for modification in self.training_modifications:
                commands += modification.encode()
        else:
            if self.training_modifications:
                commands += ['  TRAINING']
                for modification in self.training_modifications:
                    commands += modification.encode()
            if self.testing_modifications:
                commands += ['  TESTING']
                for modification in self.testing_modifications:
                    commands += modification.encode()
        return commands


@custom_repr
class Modification:
    CUSTOM_REPR_FIELDS = ('name', 'params')
    def __init__(self, name=None):
        self.name = name or 'general.match-delete-replace'
        self.params = OrderedDict({'silent': 'no'})
        if self.name == 'general.match-delete-replace':
            self.params.update([
                ('match', OrderedDict()),
                ('change', OrderedDict()),
                ('delete', []),
            ])

    def encode(self):
        commands = ['    FILTER']
        if self.name and self.name != 'general.match-delete-replace':
            commands += ['      name={}'.format(self.name)]
        # DONE: pokud má modifikátor nějaké skalární parametry, tak je můžu
        #       vypsat podobně jako name= (a radši ještě před neskaláry)
        for option, value in self.params.items():
            if option not in ('match', 'change', 'delete') and (
                    option != 'silent' or value in ('yes', 'true', '')):
                commands += ['      {}={}'.format(option, value)]
        if 'match' in self.params:
            if self.params['match']:
                commands += ['      MATCH']
            for attr, value in self.params['match'].items():
                commands += ['        {}={}'.format(attr, value)]
        if 'change' in self.params:
            if self.params['change']:
                commands += ['      SET']
            for attr, value in self.params['change'].items():
                commands += ['        {}={}'.format(attr, value)]
        if 'delete' in self.params:
            if self.params['delete']:
                commands += ['      DEL']
            for attr in self.params['delete']:
                commands += ['        {}'.format(attr)]
        return commands


class SpecParser:  # ParamParser
    """
    tagsetbench:run?COMMON;id=ordinals-fixed-first;
    FILTER;name=general.match-delete-replace;MATCH;lc=\d\.;SET;x=O;
    FILTER;name=general.match-delete-replace;MATCH;k=4;x=O;SET;k=2

    tagsetbench:run?COMMON;id=pokus-co-smazu;MATCH;lc=\d\.;SET;x=O;
    FILTER;MATCH;k=4;x=O;SET;k=2

    python models.py '
    EVALUATE
      tagger=rftagger
      bootstrap=no
      rftagger-context-length=5
      external=baseline-unmodified
      TRAINING_TESTING
        FILTER
          alias=hyphen
          MATCH
            word=-
            k=\?
          SET
            tag=kIx~
    COMMON
      id=unmodified_vs_hyphen
      corpus-portions=quarters
    '
    """
    def __init__(self, spec):
        self.spec = spec

    def parse(self):
        self.start()

        for param in self.params:
            # ignore empty tokens and comments
            if not param[0] or param[0][0] in '#%':
                continue
            if param[0] == 'COMMON':  # TODO: COMPARE (podle textu)
                self.implicitly_add_modification()
                # TODO: možná vynulovat i ostatní věci?
                self.modification = None
            elif param[0] == 'EVALUATE':
                self.close_modification_if_any()
                self.add_compared_side()
            elif param[0] in ('TRAINING_TESTING', 'TRAINING', 'TESTING'):
                self.implicit_side()
                self.set_modifications_target(param[0])
            elif param[0] == 'FILTER':
                self.implicit_side()
                if self.modifications is None:
                    self.set_modifications_target('TRAINING_TESTING')
                self.close_modification_if_any()
                self.modification = Modification()

            if param[0] in ('COMMON', 'EVALUATE', 'TRAINING_TESTING',  # TODO: COMMON → COMPARE
                            'TRAINING', 'TESTING', 'FILTER', 'MATCH', 'SET',
                            'DEL'):
                self.parsing = param[0]
            elif len(param) == 2:
                self.handle_named_value(*param)
            elif len(param) == 1:
                self.handle_single_value(param[0])

        # pokud nebylo na konci COMMON
        self.implicitly_add_modification()

        return self.parsed

    def start(self):
        tokens = self.spec.replace('\;', 'SEMICOLON').replace(
            '\n', ';').split(';')
        self.params = [token.strip().replace('SEMICOLON', ';').split('=', 1)
                       for token in tokens]

        self.parsed = ModificationParams()
        self.compared_side = None
        self.modifications = None  # list (currently, either training_ or testing_)
        self.modification = None
        self.options = None
        self.parsing = 'EVALUATE'

    def add_compared_side(self):
        self.compared_side = ComparedSide()
        self.parsed.sides.append(self.compared_side)
        self.options = self.compared_side.options

    def implicit_side(self):
        if not self.compared_side:
            self.add_compared_side()

    def set_modifications_target(self, target):
        if target == 'TRAINING':
            self.modifications = self.compared_side.training_modifications
        elif target == 'TESTING':
            self.modifications = self.compared_side.testing_modifications
        else:
            self.modifications = self.compared_side.testing_modifications = \
                self.compared_side.training_modifications

    def implicitly_add_modification(self):
        if self.modification:
            if self.modifications is None:
                self.implicit_side()
                self.set_modifications_target('TRAINING_TESTING')
            self.modifications.append(self.modification)

    def close_modification_if_any(self):
        if self.modification:
            self.modifications.append(self.modification)
        self.modification = None

    def handle_single_value(self, value):
        if self.parsing == 'DEL':
            if not self.modification:
                self.modification = Modification()
            delete = self.modification.params.setdefault('delete', [])
            delete.append(value)
        elif self.parsing == 'FILTER':
            # simply stating a modifier/modification name creates it implicitly
            self.modification = Modification(name=value)
        elif self.parsing == 'PARAM':  # DICT/MAP?
            # WISH: vlastní slovníky a koukání do/práce v kontextu?
            # PARAM;name=match;offset=-1;k=7;c=(\d);
            # PARAM;name=set;offset=0;c=\1            to by bylo asi už moc ;-)
            pass

    def handle_named_value(self, key, value):
        if self.parsing in ('MATCH', 'SET'):
            if not self.modification:
                self.modification = Modification()
        if self.parsing == 'EVALUATE':
            self.implicit_side()
            self.options[key] = value
        elif self.parsing in ('TRAINING_TESTING', 'TRAINING', 'TESTING'):
            self.options[key] = value
        elif self.parsing == 'MATCH':
            match = self.modification.params.setdefault('match', OrderedDict())
            match[key] = value
        elif self.parsing == 'SET':
            change = self.modification.params.setdefault('change',
                                                         OrderedDict())
            change[key] = value
        elif self.parsing == 'COMMON':
            self.parsed.options[key] = value
        elif self.parsing == 'FILTER':
            if key == 'name':
                self.modification.name = value
            else:
                self.modification.params[key] = value


def parse(spec):
    parser = SpecParser(spec)
    return parser.parse()


if __name__ == '__main__':
    import sys
    parsed = parse(sys.argv[1])
    print('\n'.join(parsed.encode()))
