from collections import OrderedDict
from pathlib import PosixPath


with PosixPath(__file__).with_name('template.html').open() as f:
    raw_template = f.read()

before_content, after_content = raw_template.split('\n{content}\n')


# TODO: možná vyhodit?
def header(title='', argv=None):
    if not argv:
        argv = {}

    return before_content.format(title=title, input_params=argv)


def evaluation_summary(side, summary):
    # layout tabulek:
    # horizontální záhlaví se tolika sloupci, kolik je atributů
    # anebo se sloupci, které odpovídají přímému/nepřímému vyhodnocení
    # ⇒ všechny atributy vedle sebe a přímý s nepřímýma hned vedle sebe

    # header with attributes
    attributes = list(sorted(attrs for (attrs, values) in summary.items() if
                             isinstance(values, dict)))
    value_names = {
        'precision': 'Token precision',  # TODO: ještě Sentence precision?
        'correct': 'Correct tokens',
        'total': 'Total tokens',
    }

    # reference, compared or difference
    yield '<tr><th>{}<th><td colspan="20">{}</td></tr>'.format(side,
        '')  # BYLY: změny
    yield '<tr><th>{}</th></tr>'.format(
        '</th><th>'.join([''] + attributes + [''])  # side cells blank
    )
    for value in ('precision', 'correct', 'total'):
        yield '<tr><th>{}</th><td>{}</td><th>{}</th></tr>'.format(
            value_names[value],
            '</td><td>'.join(str(summary[attr][value]) for attr in attributes),
            value_names[value],
        )


def evaluation_summary_sides_horizontal(attr, summary):
    value_names = OrderedDict([
        ('total', 'Total tokens'),
        ('correct', 'Correct tokens'),
        ('precision', 'Category accuracy'),
        # TODO: overall accuracy (prostě poměr počtu chyb/správnejch a všech
        #       tokenů, jako mám v přehledech skupin/clusterů chyb)
        # TODO: ještě Sentence precision?
    ])

    header = [attr] + list(value_names.values())
    yield from simple_table([], header, enclose_in_tags=False)

    sides = ['reference', 'compared', 'difference']  # TODO: 'gain'
    for side in sides:
        yield table_row([side] +
                        [summary[side][attr][value] for value in value_names])


# TODO: přepínač, jestli vypsat i <table> a </table>
# DONE: zatím napevno, možná přibyde kdyžtak <table id="{table_id}"
#                                                   class="{table_class}">
def simple_table(sorted_list, columns=None, header_lines=0,
                 enclose_in_tags=True, footer=False):
    if enclose_in_tags:
        yield '<table>'

    headers = []
    if columns:
        headers.append(columns)

    rows = iter(sorted_list)

    for i in range(header_lines):
        headers.append(next(rows))

    for header in headers:
        # TODO: využít funkci table_row, až bude zobecněná
        yield '<tr><th>{}</th></tr>'.format(
            '</th><th>'.join(header),
        )

    for row in rows:
        yield table_row(row)

    if footer:
        for header in reversed(headers):
            yield '<tr><th>{}</th></tr>'.format(
                '</th><th>'.join(header),
            )

    if enclose_in_tags:
        yield '</table>'


# TODO: nějak to zobecnit, aby to mohla využít funkce simple_table?
#       – třeba s pomocí druhýho seznamu, kde bude True/False podle toho,
#         jestli jde obyč buňku/záhlaví (a prostě bych to zipoval_longest)
def table_row(values):
    # return '<tr><th>{}</th>{}</tr>'.format(
    #     header, ''.join('<td>{}</td>'.format(value) for value in values))
    return '<tr>{}</tr>'.format(
        ''.join('<td>{}</td>'.format(format_value(value)) for value in values))


# protistrana (která to parsuje) je v compare_evaluation.py
def format_value(value):
    if isinstance(value, float):
        return format(value, '0.3%')
    else:
        return value
