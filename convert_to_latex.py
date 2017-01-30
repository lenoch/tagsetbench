#!/usr/bin/env python3
import re
import sys

from bs4 import BeautifulSoup
# community/python-pyperclip 1.5.27-1 [installed]
#     A cross-platform clipboard module for Python
# community/xsel 1.2.0.20160929-1 [installed]
#     XSel is a command-line program for getting and setting the contents of the X selection
import pyperclip
from tabulate import tabulate

from tagsetbench import read_args

OPTIONS = {
    'drop-last-column': False,
    'drop-third-columns': False,
}


def convert_to_latex(html=None, copy_to_clipboard=False, name=None,
                     save_to_file=False, drop_last_column=False,
                     drop_third_columns=False):
    if html is None:
        html = sys.stdin.read()
    soup = BeautifulSoup(html, 'html5lib')  # html.parser gets <br> wrong
    for br in soup('br'):
        br.replace_with('\n')

    rows = soup('tr')  # assuming no nested tables
    # if table('tr')[0]('th'):
    #     first_row = table('tr')[0].replace_with('')
    #     header = [cell.text for cell in first_row('th')]
    # else:
    #     header = []
    # data = [[cell.text for cell in row] for row in table('tr')])
    contains_header = 'firstrow' if rows[0]('th') else None
    data = []

    # TODO: pamatovat si, v který jsem buňce
    stupid_extra_rows = []
    # TODO: kdykoli pak v nějaký bude víc řádků, tak může využít tyhle extra,
    #       anebo je přidat
    # TODO: extra řádky se zpracujou přednostně (před plnohodnotnejma;
    #                                            jo, připomíná mi to presety)
    # TODO: samozřejmě z těch více řádků v buňce zůstane pak jenom jeden

    for row in rows:
        cells = []
        source_cells = row('td') or row('th')
        if drop_third_columns:
            new_cells = [source_cells[0]]  # “left side header”
            for i in range(len(source_cells) - 1):
                if i % 3:
                    new_cells += [source_cells[i]]
            source_cells = new_cells
        if drop_last_column:
            source_cells.pop()
        for cell in source_cells:
            cell_content = cell.text.replace('↔', '/')
            cell_content = cell.text.replace(' ', '_')
            if '\n' in cell_content:
                nested_rows = [[line] for line in cell_content.split('\n')]
                fancy_nested_table = tabulate(nested_rows, tablefmt='latex')
                plain_table = fancy_nested_table.replace('\\hline\n', '').replace('{r}', '[t]{r}')
                cells += [_preserve_latex(plain_table)]
            else:
                cells += [cell_content]
        data += [cells]

    # NOTE: asi už to není aktuální
    # http://stackoverflow.com/questions/35418787/generate-proper-latex-table-using-tabulate-python-package
    # tabulate.LATEX_ESCAPE_RULES={}
    if contains_header:
        data[0][0] = 'PERCENT'
    # latex = _unhide_latex(tabulate(data, headers='firstrow', tablefmt='latex_booktabs'))
    latex = tabulate(data, headers='firstrow', tablefmt='latex_booktabs')
    latex = latex.replace(r'\%', '')
    latex = latex.replace('PERCENT', '\%')
    latex = latex.replace('číslo ', 'number')
    latex = latex.replace('všechno', 'tag    ')
    latex = latex.replace('-', '$-$')
    latex = latex.replace(r'\_/\_', r'\,/\,')
    latex = latex.replace(r'\_', r' ')
    latex = re.sub(r'^\s*((?:[a-zA-Z0-9/.]|\\,)+)', r' \\texttt{\1}', latex,
                   flags=re.MULTILINE)
    lines = latex.split('\n')
    # TODO: to p{} zřejmě zarovnává vlevo – a pak ty moje vnitřní tabulky vpravo
    lines[0] = '\\begin{longtable}[]{@{}|l|' + '|p{6.5mm}r'*len(data[0]) + '|@{}}'  # 8mm
    # https://en.wikibooks.org/wiki/LaTeX/Tables#The_tabular_environment
    # → tak teda rp?

    caption = ''
    if name is not None:
        caption = ('\\caption{Evaluation of \\texttt{' +
                   name.replace('_', '\\_') + '} (all values in \%)}\n')
    lines[-1] = caption + lines[-1].replace('tabular', 'longtable')
    for i, line in enumerate(lines):
        line = line.strip()
        if line.startswith('&'):
            lines[i] = re.sub(' +', ' ', line)
    latex = '\n'.join(lines)
    if copy_to_clipboard:
        pyperclip.copy(latex)
    if name and save_to_file:
        with open('/home/Škola/Diplomka/TeX/results/{}.tex'.format(
                name), 'w') as f:
            print(latex, file=f)
            # f.write(latex + '\n')
    return latex


PRESERVE_LATEX = (
    ('\\', 'BACKSLASH'),
    ('{', 'CURLY-OPENING'),
    ('}', 'CURLY-CLOSING'),
)


def _preserve_latex(text):
    for save_me, cover in PRESERVE_LATEX:
        text = text.replace(save_me, cover)
    return text


def _unhide_latex(text):
    for save_me, cover in PRESERVE_LATEX:
        text = text.replace(cover, save_me)
    return text


if __name__ == '__main__':
    name = None
    if len(sys.argv) > 1:
        name = sys.argv[1]
    args = read_args(sys.argv, OPTIONS)
    latex = convert_to_latex(html=None, copy_to_clipboard=True, name=name,
                             save_to_file=True,
                             drop_last_column=args['drop-last-column'],
                             drop_third_columns=args['drop-third-columns'])
    print(latex)
