from contextlib import contextmanager
from copy import deepcopy
from pathlib import PosixPath

from log import log

# WISH: zahodit (z annotate, bootstrap, create_model, majka, makefile, split_corpus a test_configure)
ShellPath = PosixPath


class ExpandableList(list):
    def __init__(self, iterable):
        super().__init__(iterable)
        self.prepended_items = []

    def __iter__(self):
        for item in super().__iter__():
            if self.prepended_items:
                yield from self.prepended_items
                self.prepended_items = []
            yield item
        # leftovers
        if self.prepended_items:
            yield from self.prepended_items
            self.prepended_items = []


# TODO: read_params
# TODO: považovat chybějící hodnotu za chybu (nejdřív asi u skalárů, nebo i u
#       seznamů?)
def read_args(argv, args={}):
    """
    Convert argv to a dictionary of parameters.

    All parameters start with "--". Only parameters declared in the 'args'
    dictionary are understood. Their types are inferred from default values, or
    in the case of lists, from the first, sentinel value, which is removed at
    the end.
    """
    argv_expandable = ExpandableList(argv)
    argv_iter = iter(argv_expandable)
    executable = next(argv_iter)
    args = deepcopy(args)

    expected = None
    expected_action = True
    action = None  # TODO: první parametr před --

    for arg in argv_iter:
        if arg.startswith('--'):
            arg = arg[2:]
            if arg in args:
                if isinstance(args[arg], bool):
                    args[arg] = True
                expected = arg
            else:
                raise ValueError('Unknown parameter --{}'.format(arg))

        elif expected:
            # if expected == 'preset':  # shorthands for parameter combinations
            #     argv_expandable.prepended_items.extend(presets[arg]['argv'])
            #     argv_expandable.prepended_items.append('--preset')

            if isinstance(args[expected], list):
                converted_value = _convert_arg(arg, sentinel=args[expected][0])
                args[expected].append(converted_value)
            else:
                args[expected] = _convert_arg(arg, sentinel=args[expected])

            # continue reading lists; don't convert scalars to lists implicitly
            # (yet); allow replacing scalars (for now)
            if not isinstance(args[expected], list):
                expected = None

    _remove_sentinels_from_lists(args)

    # WISH: args['cwd'] = PosixPath(__file__), ale to musí předat volající
    args['argv'] = argv
    return args


def _convert_arg(value, sentinel=None):
    if isinstance(sentinel, bool):
        return value.lower() in ('yes', 'true', 'on', '1')
    elif isinstance(sentinel, int):
        try:
            return int(value)
        except ValueError:
            return None
    elif isinstance(sentinel, PosixPath):
        return PosixPath(value)
    else:
        return value


def _remove_sentinels_from_lists(args):
    for option, value in args.items():
        if isinstance(value, list):
            # log.debug('Removing sentinel value from option %s: %r', option,
            value.pop(0)


def serialize_input_params(args):  # JSONize
    args = deepcopy(args)
    for key, value in args.items():
        if isinstance(value, PosixPath):
            args[key] = str(value)
        elif isinstance(value, list):
            for i, item in enumerate(value):
                if isinstance(item, PosixPath):
                    value[i] = str(item)
    return args


# TODO: někde podpořit i in-line výpis (ale asi radši obarvenej):
#
# <s p="59%">"/"/kIx"<g/>Až/až/k6eAd1 v/v/k7c6 dopise/dopis/k1gInSc6 ze/z/k7c2
# <phr w="16." l="##." t="k2gInSc2xO">16/##/k4<g/>././kIx. </phr>
# července/červenec/k1gInSc2 mi/já/k3xPp1nSc3 …
#
# místo tabulátorů / a // zas místo / s tím, že by byly zakázaný prázdný hodno-
# ty; musely by se nahrazovat za nějakej placeholder, třeba EMPTY nebo něco
# chytřejšího
#
# anebo případně jinej oddělovač (Unicode má úzkou mezeru)
#
# místo <g/> by šlo takový to mezerový podtržítko („tisknutelná mezera“)
def print_sentence(sentence, output_fd):
    print('<{} number="{}">'.format(sentence.kind, sentence.number),
          file=output_fd)
    for line in sentence.tokens:
        print(line, file=output_fd)
    print('</{}>'.format(sentence.kind), file=output_fd)


# Functions used in evaluation (gone)

# Functions used in tests

def assert_equal(computed, expected):
    if computed is not expected:
        if not (isinstance(computed, str) or isinstance(expected, str)):
            log.warning('%s is not identical to %s', computed, expected)
        if computed != expected:
            raise AssertionError('{} != {}'.format(computed, expected))
    # log.info('OK  %s == %s', computed, expected)


@contextmanager
def assert_raises(error):
    try:
        yield
    except error as e:
        log.debug('correctly raised %s(%s)', error.__name__, e)
    else:
        raise AssertionError('{} was not triggered'.format(error.__name__))


def custom_repr(cls):
    def repr_with_custom_fields(cls):
        # NOTE: names of fields must not lead to cycles (e.g. through parent-
        #       child relations)
        fields_and_values = ('='.join((field, repr(getattr(cls, field))))
                             for field in cls.CUSTOM_REPR_FIELDS)
        # asi bych si měl tu rekurzi nahoře přepsat spíš na procházení
        # zásobníku, abych měl přehled o úrovni zanoření…
        return '{}({})'.format(cls.__class__.__name__,
                               ',\n\t'.join(fields_and_values))  # ', '

    cls.__repr__ = repr_with_custom_fields
    return cls
