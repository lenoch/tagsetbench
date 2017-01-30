#!/usr/bin/env python3
from collections import OrderedDict
from pathlib import PosixPath
import subprocess
import sys
import textwrap

from bs4 import BeautifulSoup  # Arch: community/python-beautifulsoup4 4.5.1-1

import html_writer
from tagsetbench import read_args

RESULTS_LOCALHOST = '/home/Diplomka/working_dir'
RESULTS_AURORA = '/home/xsvobo15/working_dir'
RESULT_FILE = 'clustered-errors-overview.html'

OPTIONS = {
    'fold': '0-75_75-100',
    'measurements': ['context-length-2'],
    'merged-comparison': PosixPath(),
    'sort-by-first-compared': False,
    'folds': [''],
    'measurement': '',
    'host': '',
    'date-time': '',  # WISH: předávat volitelně i datum a čas
}

FOLDS = {
    '25-100_0-25': 'I.',
    '0-25,50-100_25-50': 'II.',
    '0-50,75-100_50-75': 'III.',
    '0-75_75-100': 'IV.',
}


class MergeEvaluations:  # TODO: tohle je název akce, chce to spíš …?
    def __init__(self, argv):
        self.args = read_args(argv, OPTIONS)
        # one measurement, multiple folds with their own baselines/references
        self.folds = self.args['folds']
        self.measurement = self.args['measurement']
        # multiple measurements, shared baseline/reference, one fold
        self.fold = self.args['fold']
        self.measurements = self.args['measurements']
        self.host = self.args['host'] or 'localhost'
        # if not self.measurements:
        #     self.host = 'localhost'
        self.date_time = self.args['date-time']

    def run(self):
        if self.args['folds']:
            self.merge_related_folds()
        else:
            self.merge_foreign_folds()

    def merge_related_folds(self):
        """
        Merge folds of one measurement (with multiple baselines/references)
        into a single table.
        """
        separate_results = OrderedDict(
            (f, self.fetch_result(self.measurement, f))
            for f in self.folds)
        first_result = separate_results[self.folds[0]]
        attrs = list(first_result)

        if self.args['sort-by-first-compared']:
            attrs = [attr_val[0] for attr_val in sorted(
                first_result.items(), key=lambda attr_val:
                attr_val[1]['count-compared'], reverse=True)]

        compared_name = self.measurement
        if '__vs__' in compared_name:
            compared_name = compared_name[compared_name.index('__vs__')+6:]
        elif '_vs_' in compared_name:
            compared_name = compared_name[compared_name.index('_vs_')+4:]

        header = ['']
        for fold in self.folds:
            # adresu u místního srovnání znám
            if self.host == 'localhost':
                header += ['<a href="{0}/{1}">{2}</a>'.format(
                    fold, RESULT_FILE, FOLDS.get(fold, fold)),
                    'diff.', shorten(compared_name)]
            else:
                header += ['<a href="http://nlp.fi.muni.cz/~xsvobo15/'
                           'tagsetbench/{0}">{1}</a>'.format(
                               self.measurement, FOLDS.get(fold, fold)),
                           'diff.', shorten(compared_name)]
        header += ['avg.', 'diff.', shorten(compared_name)]
        header += ['']

        rows = []
        for attr in attrs:
            cells = []
            avg_percent_difference_ref = 0
            avg_percent_difference_diff = 0
            avg_percent_difference_subj = 0
            for result in separate_results.values():
                percent_difference_ref = (result[attr]['count-reference'] /
                                          result['tokens']['count-reference'])
                percent_difference_subj = (result[attr]['count-compared'] /
                                           result['tokens']['count-compared'])
                percent_difference_diff = (percent_difference_subj -
                                           percent_difference_ref)
                cells += ['<span title="{0}">{1:0.3%}</span>'.format(
                              # reference
                              result[attr]['count-reference'],
                              percent_difference_ref),
                          '<span title="{0}">{1:0.3%}</span>'.format(
                              # difference
                              result[attr]['count-compared'] -
                              result[attr]['count-reference'],
                              percent_difference_diff),
                          '<span title="{0}">{1:0.3%}</span>'.format(
                              # “subject” of comparison
                              result[attr]['count-compared'],
                              percent_difference_subj)]

                # diff = (result[attr]['count-compared'] -
                #         result[attr]['count-reference'])
                diff = percent_difference_diff
                if diff < -0.0002:
                    cells[-2] = '<span class="lower">{}</span>'.format(
                        cells[-2])
                if diff > 0.0002:
                    cells[-2] = '<span class="higher">{}</span>'.format(
                        cells[-2])

                avg_percent_difference_ref += percent_difference_ref
                avg_percent_difference_diff += percent_difference_diff
                avg_percent_difference_subj += percent_difference_subj

            # průměr
            avg_percent_difference_ref /= 4
            avg_percent_difference_diff /= 4
            avg_percent_difference_subj /= 4
            cells += ['{0:0.3%}'.format(
                          # reference
                          avg_percent_difference_ref),
                      '{0:0.3%}'.format(
                          # difference
                          avg_percent_difference_diff),
                      '{0:0.3%}'.format(
                          # “subject” of comparison
                          avg_percent_difference_subj)]
            diff = avg_percent_difference_diff
            if diff < -0.0002:
                cells[-2] = '<span class="lower">{}</span>'.format(
                    cells[-2])
            if diff > 0.0002:
                cells[-2] = '<span class="higher">{}</span>'.format(
                    cells[-2])

            rows.append([attr] + cells + [attr])

        with self.args['merged-comparison'].open('w') as summary:
            print(html_writer.header(
                # '{} {}'.format(self.measurement, ' '.join(self.folds)),
                self.measurement,
                argv=self.args['argv']), file=summary)

            print('<table id="compared-parts">', file=summary)
            for line in html_writer.simple_table([header] + rows,
                                                 header_lines=1, footer=True,
                                                 enclose_in_tags=False):
                print(line, file=summary)
            print('</table>', file=summary)

            print(html_writer.after_content, file=summary)

    def merge_foreign_folds(self):
        """
        The measurements are relatives (share a baseline/reference).
        """
        separate_results = OrderedDict(
            (m, self.fetch_result(m, self.fold)) for m in self.measurements)
        for measurement, result in tuple(separate_results.items()):
            if result is None:
                del separate_results[measurement]
        measurements = list(separate_results)

        first_result = separate_results[measurements[0]]
        attrs = list(first_result)

        if self.args['sort-by-first-compared']:
            attrs = [attr_val[0] for attr_val in sorted(
                first_result.items(), key=lambda attr_val:
                attr_val[1]['count-compared'], reverse=True)]

        counts_of_correct_tokens = OrderedDict()
        counts_of_correct_tokens['reference'] = OrderedDict(
            (attr, first_result[attr]['count-reference']) for attr in attrs)
        for measurement, result in separate_results.items():
            counts_of_correct_tokens[measurement] = OrderedDict(
            (attr, result[attr]['count-compared'] if attr in result else 99999)
            for attr in attrs)

        measurements.insert(0, 'reference')

        header = ['attr'] + ['<a href="http://nlp.fi.muni.cz/~xsvobo15/'
                             'tagsetbench/{0}">count-{0}</a>'.format(m) for m
                             in measurements] + ['attr']
        rows = []
        for attr in attrs:
            values = [counts_of_correct_tokens[m][attr] for m in measurements]
            highest = max(values)
            lowest = min(values)
            lowest_diff = lowest - counts_of_correct_tokens['reference'][attr]
            cells = [
                '{}<br>{}'.format(counts_of_correct_tokens[m][attr],
                                  counts_of_correct_tokens[m][attr] -
                                  counts_of_correct_tokens['reference'][attr] -
                                  lowest_diff)
                for m in measurements]
            for i in range(len(values)):
                if values[i] == lowest:
                    cells[i] = '<span class="lowest">{}</span>'.format(
                        cells[i])
                if values[i] == highest:
                    cells[i] = '<span class="highest">{}</span>'.format(
                        cells[i])
            rows.append([attr] + cells + [attr])

        with self.args['merged-comparison'].open('w') as summary:
            print(html_writer.header(
                '{} {}'.format(self.fold, ' '.join(self.measurements)),
                argv=self.args['argv']), file=summary)

            for line in html_writer.simple_table(rows, header, footer=True):
                print(line, file=summary)

            print(html_writer.after_content, file=summary)

        # for cluster, values in pokus.items():
        #     print('\t'.join(format(col, '0.3%') if isinstance(col, float) else
        #                     str(col) for col in values.values()) + '\t' + cluster)

    def fetch_result(self, measurement='', fold=''):
        if self.host == 'aurora':
            try:
                radky = self.download_lines(measurement, fold)
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                return None
        elif self.date_time == 'latest':
            # RESULTS_LOCALHOST
            # with open(''.format) as f:
            # radky = f.readlines()
            radky = subprocess.run(
                "head -n 1000 "
                "$(ls -t {0}/{1}/*/{2}/{3} | head -n 1)".format(
                    # TODO: na Auroře je ale lokální cesta jiná, ty vole
                    RESULTS_LOCALHOST, measurement, fold, RESULT_FILE),
                shell=True, stdout=subprocess.PIPE, timeout=3,
                universal_newlines=True, check=True).stdout
        else:
            with open('{}/{}'.format(fold, RESULT_FILE)) as f:
                radky = f.read()

        po_konec_tabulky = radky[:radky.index('</table>') + len('</table>')]
        od_zacatku_tabulky = po_konec_tabulky[radky.index('<table'):]

        tabulka = BeautifulSoup(od_zacatku_tabulky, 'html.parser')
        radky = tabulka.table('tr')
        hlavicka = radky.pop(0)

        # sloupec 'cluster' bude klíč slovníku
        sloupce = ['global-accuracy-reference',
                   'global-accuracy-compared',
                   'global-accuracy-diff',
                   # correct counts
                   'count-reference',
                   'count-compared',
                   'count-diff',
                   ]

        vsechno = OrderedDict()

        for radek in radky:
            bunky = radek('td')
            cluster = bunky.pop(0).text
            hodnoty = [self.convert_value(b.text) for b in bunky]
            vsechno[cluster] = OrderedDict(zip(sloupce, hodnoty))

        return vsechno

    def download_lines(self, measurement='', fold=''):
        # v interaktivní konzoli to nečeká nebo netrvá tak dlouho, nechápu
        # proč
        r = subprocess.run("ssh xsvobo15@aurora.fi.muni.cz -n 'files=$(ls -t "
                           "{0}/{1}/{2}/{3}/{4}) && head -n 200 $(echo $files "
                           "| head -n 1)'".format(
                RESULTS_AURORA,
                measurement,
                '*' if self.date_time == 'latest' else self.date_time,
                fold,
                RESULT_FILE),
            shell=True, stdout=subprocess.PIPE, timeout=3,
            universal_newlines=True, check=True)  # stderr=subprocess.PIPE
        # http://superuser.com/questions/363444/how-do-i-get-the-output-and-exit-value-of-a-subshell-when-using-bash-e
        return r.stdout

    def convert_value(self, value):
        if value.endswith('%'):
            return float(value[:-1]) / 100
        if '.' in value and not re.search('[^0-9.]', value):
            return float(value)
        try:
            return int(value)
        except ValueError:
            return value


def shorten(name):
    return textwrap.shorten(name.replace('-', ' '), width=15,
                            placeholder='...').replace(' ', '-')


if __name__ == '__main__':
    aggregator = MergeEvaluations(sys.argv)
    aggregator.run()
