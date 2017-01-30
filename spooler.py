#!/usr/bin/env python3
from contextlib import suppress
from datetime import datetime
# http://stackoverflow.com/questions/9877462/is-there-a-python-equivalent-to-
# the-which-command
from distutils.spawn import find_executable
import json
from pathlib import PosixPath
from subprocess import run, CalledProcessError
import sys
from time import sleep

from log import INFO, log, set_log_level
from tagsetbench import read_args


OPTIONS = {
    'make-executable': False,
    'jobs-dir': 'spool',  # TODO: a vymyslet
}

POLLING_INTERVAL = 5  # seconds
JOBS_DIRECTORY = 'spool'
DONE_DIRECTORY = 'spool/done'
RETRIES = 5  # before being moved to 'spool/failed'
FAILED_DIRECTORY = 'spool/failed'

# TODO: měl by si vytvářet podadresáře sám


class Spooler:
    """
    TODO:
    – logování

    – zabil jsem create_model.py, díky tomu neúspěšně skončil make… jenže
      rft-train běžel dál… takže systemd se přece jenom hodí (ale považuju to
      za chybu 'make' – anebo bych teda využil systemd-run, když existuje?)
    – aur/(general-)spooler?
      – ale to bych musel přejít na argparse nebo něco takovýho, prostě co
        nejmíň závislostí i směrem k vlastním knihovnám (read_args i log)
    – oddělit pak kdyžtak job.py (anebo ne? aby šel prostě vzít spooler.py a
      hotovo?)
    """
    def __init__(self, argv=None):
        self.args = read_args(argv, OPTIONS)
        self.finished_dir = PosixPath(DONE_DIRECTORY)
        self.failed_dir = PosixPath(FAILED_DIRECTORY)
        self.systemd_run = find_executable('systemd-run')

    # špulka už je namotaná, to jméno se opakuje
    # (jak se to řekne odborně? „DVD disk“ a podobně)
    def loop(self):
        while True:
            self.process_jobs()
            sleep(POLLING_INTERVAL)

    def process_jobs(self):
        jobs = self.read_jobs()

        while jobs:
            job = Job(path=jobs.pop(0), spooler=self)
            job.run()

            if not jobs:
                jobs = self.read_jobs()

    def read_jobs(self):
        # nemůžu si držet file descriptor, protože se může stát, že si adresář
        # s úkolama smažu – a když vytvořím novej, půjde o jinej inode
        polling_dir = PosixPath(JOBS_DIRECTORY)

        try:
            files = (item for item in polling_dir.iterdir() if item.is_file()
                     or item.is_symlink())
            # TODO: po resolve() ale cíl musí bejt soubor, ale to řešit až líně
            # TODO: anebo řešit rovnou, aby se mi process_jobs mohlo ukončit,
            #       když prostě nebudou „pravý/skutečný/opravdový“ úkoly
            return sorted(files, key=lambda path: path.lstat().st_mtime)
        except FileNotFoundError:
            log.exception('Wrong working directory?')
        return []


class Job:
    def __init__(self, path, spooler):
        self.path = path
        self.spooler = spooler

    def run(self):
        # nedělat resolve, protože by to třeba procházelo skrz symlink a mazalo
        # cíl, to nechci, já chci mazat jenom to, co mám v JOBS_DIRECTORY

        # když už bych dělal symlinky, tak kvůli přesouvání do spool/done by
        # bylo lepší je dělat absolutní, abych do nich nemusel přidávat další
        # úroveň – ale klidně bych i mohl, protože jsem spooler
        if self.spooler.args['make-executable']:
            if not self.is_executable() and self.path.suffix not in ['.json',]:
                log.info('Making job "%s" executable.', self.path)
                self.make_executable()

        if self.is_executable():
            log.info('Running job "%s".', self.path)
            try:
                cmd = str(self.path)
                if self.spooler.systemd_run:
                    # http://stackoverflow.com/questions/31890970/easy-way-to-
                    # get-result-status-code-of-systemd-run-command
                    # NOTE: --scope pomohlo, --slice to jenom hierarchizuje,
                    #       ale pořád, pořád mám ten samej problém, pořád to
                    #       nezabije … aha, protože mám Type=simple!
                    # --property= ?

                    # ERROR    Command '/usr/bin/systemd-run --user --scope
                    # --slice spooler spool/desam-latest-remove-zA.sh' returned
                    # non-zero exit status 2
                    # ale pořád:
                    # ● run-r4d2bf2f009fd4a4bb8779b761dea35cb.scope - /home/
                    #   Škola/Diplomka/spool/desam-latest-remove-zA.sh
                    #    Loaded: loaded (/run/user/1000/systemd/transient/run-
                    #    r4d2bf2f009fd4a4bb8779b761dea35cb.scope; transient;
                    #    vendor preset: enabled)
                    # Transient: yes
                    #    Active: active (running) since So 2016-08-06 19:12:50
                    #    CEST; 4min 54s ago
                    #    CGroup: /user.slice/user-1000.slice/user@1000.service/
                    # spooler.slice/run-r4d2bf2f009fd4a4bb8779b761dea35cb.scope
                    #            ├─23190 rft-train preprocessed-for-training-
                    #         original+none.vert wordclass.txt trained-model-
                    #         original+none.bin -c 8 -v -o rf
                    #            └─23282 rft-train preprocessed-for-training-
                    #         abbreviations.remove-zA+none.vert wordclass.txt
                    #         trained-model-abbreviations.re
                    #
                    # srp 06 19:12:50 osvoboda systemd[746]: Started /home/
                    # Škola/Diplomka/spool/desam-latest-remove-zA.sh.
                    cmd = '{} --user --scope --slice spooler {}'.format(
                        self.spooler.systemd_run, cmd)
                completed_process = run(cmd, shell=True, check=True)
                print(completed_process)
                self.mark_finished()
            except CalledProcessError as e:
                log.error(e)
                self.mark_failed()
        # TODO: rozmyslet
        # elif self.path.suffix == '.json':
        #     pass
        else:
            log.info('Non-executable job ("%s"), not supported yet.',
                     self.path)
            self.mark_failed()

    def is_executable(self):
        return self.path.lstat().st_mode & 0o111

    def make_executable(self):
        executable_mode = self.path.lstat().st_mode | 0o111
        self.path.chmod(executable_mode)

    def mark_finished(self):
        move_to_directory_or_rename(self.path, self.spooler.finished_dir)

    def mark_failed(self):
        # TODO: možná to dát do defaultdict 'retries' (a až > RETRIES)
        # TODO: nene, prostě přesunout do spool/disabled (failing)
        move_to_directory_or_rename(self.path, self.spooler.failed_dir)


def move_to_directory_or_rename(file_path, dst_dir):
    """
    Move the file to a destination but use -2, -3 suffix if a file name already
    exists there.
    """
    dst = dst_dir / file_path.name
    if dst.is_file() or dst.is_symlink():
        # the number of copies already (file.sh, file-2.sh, file-3.sh…)
        instances = len(list(dst_dir.glob('{}*{}'.format(file_path.stem,
                                                         file_path.suffix))))
        # file-4.sh
        dst = dst_dir / '{}-{}{}'.format(file_path.stem, instances + 1,
                                         file_path.suffix)
    file_path.rename(dst)  # TODO: FileNotFoundError (možná už u dst.is_file)


if __name__ == '__main__':
    set_log_level(INFO)
    spooler = Spooler(sys.argv)
    spooler.loop()
