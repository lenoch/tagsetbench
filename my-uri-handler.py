#!/usr/bin/python
from collections import namedtuple
from contextlib import suppress
from datetime import datetime
import notify2  # AUR: python-notify2
import pathlib
from pprint import pprint
# import re
import subprocess
import sys
import urllib.parse

import models


def main(argv):
    # je tam i urlparse a urlsplit
    argv[1] = urllib.parse.unquote(argv[1])
    # TODO: tahle věc jde napsat i pomocí slovníku a deklarativně
    #       (nahradit if-elif-else za přístup do slovníku pomocí schematu)
    # TODO: komplexnější handlery ať si pouštěj programy samy
    if argv[1].startswith('okular:'):
        cmd = ['/usr/bin/okular']
        uri = argv[1][len('okular:'):]
    else:
        param = argv[1]
        uri = urllib.parse.urlparse(param)  # TODO: url místo uri?
        if uri.scheme in HANDLERS:
            handler = HANDLERS[uri.scheme]
            return handler(uri)
        else:
            raise NotImplementedError('Unknown scheme: {}'.format(argv[1]))
    subprocess.run(cmd + [uri])


def dicto(uri):
    # TODO: udělat ten switcher, co poleze do /etc/hosts anebo nějak jinak
    #       ovlivní/změní resolver
    N900_ADDR = '192.168.2.15'
    path = pathlib.PosixPath(uri.path)
    if uri.path == 'refresh':
        RECORDINGS_LIST = '/home/Git/nahrávky/seznam.html'
        RECORDINGS_NOTES = '/home/Git/Intranet/nahravky.html'
        r = subprocess.run(['/usr/bin/ssh',
                            'user@' + N900_ADDR,
                            'ls -lte /home/user/MyDocs/Dicto/'],
                           stdout=subprocess.PIPE, universal_newlines=True)
        notes = ''
        with suppress(FileNotFoundError):
            with open(RECORDINGS_NOTES) as f:
                notes = f.read()
        with open(RECORDINGS_LIST, 'w') as f:
            Recording = namedtuple('Recording', [
                'attrs', 'refs', 'user', 'group', 'size', 'weekday', 'month',
                'day', 'time', 'year', 'filename'])
            source_recordings = [Recording(*recording.split()) for recording in
                                 r.stdout.splitlines()]
            html_rows = ['<tr>{}</tr>\n'.format(''.join(
                '<td>{}</td>'.format(col) for col in
                # TODO: tady předělat ten odkaz na "dicto:fetch?soubor.wav"
                ('<a href="dicto:{0}">{0}</a>{1}'.format(
                    r.filename, ' <a href="/intranet/nahravky.html#{0}">🖍</a>'.format(r.filename) if r.filename in notes else ''),  # ✅📝
                 r.size, r.weekday, r.month, r.day, r.time,
                 r.year, '<a href="dicto:transcribe?{0}">přepsat</a>'.format(
                    r.filename)))) for r in source_recordings]
            print(HTML_TEMPLATE.format('Seznam nahrávek',
                                       ''.join(html_rows)), file=f)
    elif uri.path == 'transcribe':
        path = pathlib.PosixPath(uri.query)

        # TODO: fuj, duplikovaný zespodu
        if not path.is_absolute():
            path = pathlib.PosixPath('/home/Git/nahrávky') / path.name
            if not path.suffix:
                path = path.with_suffix('.wav')
            if not path.name.startswith('an-'):
                path = path.with_name('an-' + path.name)
        if not path.exists():
            r = subprocess.run(['/usr/bin/scp',
                                'user@{}:/home/user/MyDocs/Dicto/{}'.format(
                                    N900_ADDR, path.name), str(path)])
            print(r.stderr)

        # https://github.com/Uberi/speech_recognition/blob/master/examples/
        # audio_transcribe.py
        import speech_recognition as sr
        r = sr.Recognizer()
        with sr.AudioFile(str(path)) as source:
            duration = source.FRAME_COUNT / source.SAMPLE_RATE
            audio = r.record(source) # read the entire audio file

        # language = 'fr-FR'
        language = 'en-US'
        try:
            result = r.recognize_sphinx(audio, language=language,
                                        show_all=True)
            transcription = result.hyp().hypstr
        except sr.RequestError as e:
            transcription = "Sphinx error; {0}".format(e)

        from datetime import datetime, timedelta

        frames = result.n_frames()
        interactive = []
        subtitles = []
        segments = list(result.seg())
        for i, seg in enumerate(segments, 1):
            start = duration * seg.start_frame / frames
            interactive.append('<a href="dicto:{}#t={:.2f}">{}</a>'.format(
                uri.query, start, seg.word.replace('<', '&lt;').replace(
                    '>', '&gt;')))
            sub_start = (datetime.min + timedelta(seconds=start)).strftime(
                '%H:%M:%S,%f')[:-3]
            end = duration * seg.end_frame / frames
            sub_end = (datetime.min + timedelta(seconds=end)).strftime(
                '%H:%M:%S,%f')[:-3]
            subtitles.append('{}\n{} --> {}\n{}\n'.format(
                i, sub_start, sub_end, seg.word))

        path = path.with_suffix('.html')
        with path.open('w') as f:
            print(HTML_TEMPLATE.replace('<table>', '').format(
                path, '\n'.join(interactive)), file=f)

        cmd = ['/usr/bin/geany']
        subprocess.run(cmd + [str(path)])

        # path = path.with_suffix('.txt')
        # with path.open('w') as f:
        #     print(transcription, file=f)

        path = path.with_suffix('.srt')
        with path.open('w') as f:
            print('\n'.join(subtitles), file=f)
    else:
        # TODO: předělat na 'download?soubor' (nebo 'fetch' nebo tak nějak)
        # TODO: prostě 'play'
        if not path.is_absolute():
            path = pathlib.PosixPath('/home/Git/nahrávky') / path.name
            if not path.suffix:
                path = path.with_suffix('.wav')
            if not path.name.startswith('an-'):
                path = path.with_name('an-' + path.name)
        if not path.exists():
            r = subprocess.run(['/usr/bin/scp',
                                'user@{}:/home/user/MyDocs/Dicto/{}'.format(
                                    N900_ADDR, path.name), str(path)])
            print(r.stderr)

        # smplayer neumí překládat -ss 7, zapomíná asi na tu sedmičku nebo co…
        # mplayer i mpv podporujou -ss 7.3
        cmd = ['/usr/bin/vlc', '--play-and-exit']  # ffplay
        fragment = uri.fragment
        if fragment and fragment.startswith('t='):
            cmd += ['--start-time={}'.format(fragment[2:])]

        subprocess.run(cmd + [str(path)])


def enqueue(uri):
    # TODO: kdyžtak spustit tmux a v něm spooler (se správným adresářem)
    path = uri.path
    if uri.query == 'mgr':
        spool = '/home/Škola/Diplomka/spool'  # directory
        path = pathlib.PosixPath(uri.path)
        if not path.is_absolute():
            path = pathlib.PosixPath(MEASUREMENTS_DIR) / path.name
        cmd = ['/usr/bin/cp', '--target-directory', spool]
        subprocess.run(cmd + [str(path)])
        notification = notify2.Notification(
            'Spooler on localhost', 'Queued {}'.format(uri.path),
            'applications-utilities')
        notification.show()
    elif uri.query == 'aurora':
        path = pathlib.PosixPath(uri.path)
        if not path.is_absolute():
            path = pathlib.PosixPath(MEASUREMENTS_DIR) / path.name
        subprocess.run(['/usr/bin/scp',
                        str(path),
                        'xsvobo15@aurora.fi.muni.cz:{}'.format(SPOOL_AURORA)])
        notification = notify2.Notification(
            'Spooler on Aurora', 'Queued {}'.format(uri.path),
            'applications-utilities')
        notification.show()
    else:
        spool = '/home/Git/spool'
        cmd = ['/usr/bin/cp', '--target-directory', spool]
        subprocess.run(cmd + [str(path)])


def spooler(uri):
    if uri.path == 'list-queue':
        if uri.query == 'aurora':
            ls = subprocess.run("ssh xsvobo15@aurora.fi.muni.cz -C 'cd {0}; "
                                "ls -t -r'".format(SPOOL_AURORA),
                                shell=True, stdout=subprocess.PIPE,
                                universal_newlines=True).stdout.split()
            jobs = list(filter(lambda j: j not in ('done', 'failed'), ls))
            notify2.Notification('Spooler on Aurora',
                                 'Current jobs:\n{}'.format('\n'.join(jobs)),
                                 'applications-utilities').show()


def geany(uri):
    cmd = ['/usr/bin/geany']
    if uri.fragment:
        with suppress(FileNotFoundError):
            with open(uri.path) as f:
                for n, line in enumerate(f, 1):
                    if uri.fragment in line:
                        cmd += ['--line', str(n)]
                        break
    cmd += [uri.path]
    subprocess.run(cmd)


def notes(uri):
    if uri.path == 'refresh':
        r = subprocess.run(['/usr/bin/ssh',
                            'user@192.168.2.15',
                            'ls -lte /home/user/Zápisky'],
                           stdout=subprocess.PIPE, universal_newlines=True)
        print(r.stderr)
        with open('/home/Git/Zápisky/seznam.html', 'w') as f:
            seznam = r.stdout
            print('<pre>{}</pre>'.format(seznam), file=f)
    else:
        cmd = ['/usr/bin/geany']
        path = uri.path
        subprocess.run(cmd + [path])


def tagsetbench(uri):
    blbec = uri.query
    if uri.fragment:
        blbec += '#' + uri.fragment

    if uri.path == 'compare':
        tokens = [token.split('=', 1) for token in blbec.split(';')]

        parsing = None
        fold = None
        measurements = []
        folds = []
        measurement = None
        merged = None
        sort_by = None
        host = None

        for token in tokens:
            if len(token) == 2:
                key, value = token
                if key == 'merged':  # comparison
                    merged = value  # pathlib.PosixPath(value)
                elif key == 'sort-by':
                    sort_by = value
                elif key == 'host':
                    host = value
            else:
                atom = token[0]
                if atom in ('FOLD', 'MEASUREMENTS', 'FOLDS', 'MEASUREMENT'):
                    parsing = atom
                elif parsing == 'FOLD':
                    fold = atom
                elif parsing == 'MEASUREMENTS':
                    measurements.append(atom)
                elif parsing == 'FOLDS':
                    folds.append(atom)
                elif parsing == 'MEASUREMENT':
                    measurement = atom

        cmd = ['/home/Diplomka/tagsetbench/compare_evaluation.py']
        if fold:
            cmd += ['--fold', fold]
        if measurements:
            globs = tuple(measurements)
            measurements = []
            for glob in globs:
                measurements += sorted(
                    m.replace('.sh', '') for m in subprocess.run(
                        "cd /home/Diplomka/measurements; ls {}.sh".format(
                            glob), shell=True, universal_newlines=True,
                        stdout=subprocess.PIPE).stdout.split())
            cmd += ['--measurements'] + measurements
        if folds:
            cmd += ['--folds'] + folds
        if measurement:
            cmd += ['--measurement', measurement]
        if sort_by == 'first-compared':
            cmd += ['--sort-by-first-compared']
        if merged:
            cmd += ['--merged-comparison', merged]
        if host:
            cmd += ['--host', host]

        print(' '.join(cmd))
        r = subprocess.run(cmd, stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, universal_newlines=True)
        if r.returncode == 0:
            notification = notify2.Notification(
                'Compare measurements', 'Finished {}'.format(fold or measurement),
                'applications-utilities')
            notification.show()
        else:
            for line in r.stderr.splitlines()[:25]:
                notification = notify2.Notification(
                    'Compare measurements', line, 'dialog-error')
                notification.show()

    #
    # tagsetbench:run?
    #
    # (or rather, create a script/task and open/display it)
    #

    elif uri.path == 'run':
        parsed = models.parse(blbec)

        if not parsed.options['id']:
            parsed.options['id'] = format(datetime.now(), '%Y%m%d-%H%M%S')
        open_generated_runner = parsed.options.pop('open', 'yes')

        long_form = '\n'.join(parsed.encode())
        # parsed.options['open'] = 'no'
        short_form = ';'.join(part.strip() for part in parsed.encode())
        file_name = parsed.options['id'] + '.sh'

        # with suppress(FileExistsError):
        #     with open(MEASUREMENTS_DIR + file_name, 'x') as f:
        with open(MEASUREMENTS_DIR + file_name, 'w') as f:
            print(MEASUREMENT_TEMPLATE.format(
                file_name=file_name,
                working_dir='working_dir/' + parsed.options['id'],
                specification='\n' + long_form + '\n'), file=f, end='')

        if open_generated_runner == 'yes':
            cmd = ['/usr/bin/geany']
            subprocess.run(cmd + [MEASUREMENTS_DIR + file_name])

        MEASUREMENTS_LIST = '/home/Škola/Diplomka/html/pokusy.html'

        measurements = ''
        with suppress(FileNotFoundError):
            with open(MEASUREMENTS_LIST) as f:
                measurements = f.read()

        template_start = SUMMARY_TEMPLATE_BEGIN.format(
            alias=parsed.options['id'])

        result_local = parsed.options['id']
        ls = subprocess.run("cd {0}; ls -t -d -F {1}/* | "      'grep "/$" |'
                            "head -n 1".format(RESULTS_LOCAL,
                                               parsed.options['id']),
                            shell=True, stdout=subprocess.PIPE,
                            universal_newlines=True).stdout
        if ls:
            result_local = ls.strip() + 'compared_parts.html'

        result_aurora = parsed.options['id']
        ls = subprocess.run("ssh xsvobo15@aurora.fi.muni.cz -C 'cd {0}; ls -t "
                            """-d -F {1}/* | grep "/$" | """
                            "head -n 1'".format(RESULTS_AURORA,
                                                parsed.options['id']),
                            shell=True, stdout=subprocess.PIPE,
                            universal_newlines=True).stdout
        if ls:
            result_aurora = ls.strip() + 'compared_parts.html'
        measurement = SUMMARY_TEMPLATE.format(alias=parsed.options['id'],
                                              query=short_form,
                                              result_aurora=result_aurora,
                                              result_local=result_local)

        if template_start not in measurements:
            measurements = measurements.replace(TARGET_TABLE_END, measurement +
                                                TARGET_TABLE_END)
        else:
            template_end = SUMMARY_TEMPLATE_END.format(
                alias=parsed.options['id'])
            replacement_start = measurements.index(template_start)
            replacement_end = measurements.index(template_end)

            # WISH: .index('<a href="') a potom všechno od "> až po <br>
            #       ale radši asi regexem, ať je to čitelnější
            original_measurement = measurements[replacement_start:
                                                replacement_end]
            link_start = original_measurement.index('<a href="')
            link_end = original_measurement.index('">', link_start)
            description_end = original_measurement.index('<br>', link_end)
            description = original_measurement[link_end+2:description_end]

            measurement = SUMMARY_TEMPLATE.replace(
                '{alias}</a>', '{description}').format(
                    alias=parsed.options['id'], query=short_form,
                    result_aurora=result_aurora, result_local=result_local,
                    description=description)

            measurements = (measurements[:replacement_start] + measurement +
                            measurements[replacement_end+len(template_end):])

        with open(MEASUREMENTS_LIST, 'w') as f:
            print(measurements, file=f, end='')

    else:
        # TODO: chyba, otevírám zdroják (předělat na výjimku?)
        cmd = ['/usr/bin/geany']
        path = '/home/Git/magic-links/my-uri-handler.py'
        params = ['--line', '256']
        subprocess.run(cmd + [path] + params)


MEASUREMENTS_DIR = '/home/Škola/Diplomka/measurements/'


HANDLERS = {
    'geany': geany,
    'dicto': dicto,
    'notes': notes,
    'tagsetbench': tagsetbench,
    'enqueue': enqueue,  # WISH: přesunout pod spooler:enqueue?cmd.sh
    'spooler': spooler,
}


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="cs">
<head>
<meta http-equiv="content-type" content="text/html; charset=UTF-8">
<link rel="stylesheet" type="text/css" href="/styl.css">
<title>🎙 {0}</title>
</head>
<body>
<div id="content">
<nav><ul>
    <li><a href="/intranet/rozcestnik.html">🌐 rozcestník</a></li>
    <li><a href="/intranet/nahravky.html">🎙 nahrávky</a></li>
    <li><a href="/intranet/cokoli.html">💥 zápisky</a></li>
    <li><a href="/intranet/wishlist.html">⭐ wishlist</a></li>
    <li><a href="geany:/home/Git/nahrávky/seznam.html">🖍&nbsp;upravit</a></li>
</ul></nav>

<h1>🎙 {0}</h1>

<p>🎙 <a href="dicto:refresh">natáhnout znova</a></p>
<!-- ikonka stahování dat -->

<ul>
    <li><mark>TODO</mark>: zobrazovat volné místo, aby mi nedošlo, když se mi
        to zrovna nehodí</li>
    <li><strong>TODO</strong>: označovat soubory, které už mám přehrané</li>
    <li>TODO: <a href="geany:/home/Git/magic-links/my-uri-handler.py">tuhle
        šablonu</a> možná dát mimo pythonovskej zdroják, aby se líp upravovalo
        HTML?</li>
</ul>

<table>
{1}</table>

</div>
</body>
</html>"""


MEASUREMENT_TEMPLATE = """#!/bin/sh
# {file_name}
WORKING_DIRECTORY=$(
tagsetbench/configure --working-dir {working_dir} \\
                      --specification '{specification}'
);
EXIT_CODE=$?
if [ $EXIT_CODE -eq 0 ]; then
    MAKE_COMMAND="make --jobs 8 -C '$WORKING_DIRECTORY' -f Makefile"
    echo $MAKE_COMMAND
    eval $MAKE_COMMAND
fi;
"""


RESULTS_AURORA = '/home/xsvobo15/working_dir'
RESULTS_LOCAL = '/home/Škola/Diplomka/working_dir'
TARGET_TABLE_END = '</table><!-- id="tabulka-mereni" -->'

# 💡 <a href="tagsetbench:result?{alias}&amp;ungrouped-errors">TODO: rychlej odkaz</a>
# ?C=M;O=D
SUMMARY_TEMPLATE = """    <tr id="strucne-{alias}">
        <td>🏗 <a href="tagsetbench:run?{query}">{alias}</a><br>
            🎬 <a href="enqueue:{alias}.sh?mgr">lokálně</a>
            🎬 <a href="enqueue:{alias}.sh?aurora">na Auroře</a></td>
        <td>📏 <a href="/measurements/{result_local}">tady</a><br>
            📏 <a href="http://nlp.fi.muni.cz/~xsvobo15/tagsetbench/{result_aurora}">Aurora</a></td>
        <td>❓ <a href="text.html#{alias}">komentář</a></td>
    </tr><!-- id={alias} -->
"""

SUMMARY_TEMPLATE_BEGIN = '    <tr id="strucne-{alias}">\n'
SUMMARY_TEMPLATE_END = '    </tr><!-- id={alias} -->\n'

SPOOL_AURORA = '/home/xsvobo15/spool'


if __name__ == '__main__':
    notify2.init('URI 4 Life')
    main(sys.argv)
