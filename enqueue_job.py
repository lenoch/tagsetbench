#!/usr/bin/env python3
from contextlib import suppress
from datetime import datetime
import json
from pathlib import PosixPath
from subprocess import run, CalledProcessError
import sys
from time import sleep

from log import INFO, log, set_log_level
from tagsetbench import read_args

OPTIONS = {
    'job': PosixPath(''),
    'host': 'xsvobo15@aurora.fi.muni.cz',
    'spool-path': '/home/xsvobo15/spool',
}


def enqueue_job():
    """
    Add a job to the spooler directory. Rename it (by adding a "-123" suffix)
    if it already exists in the directory itself or in "done" or "failed", too.
    """
    args = read_args(sys.argv, OPTIONS)

    if args['host']:
        cmd = ['scp',
               str(args['job']),
               '{}:{}'.format(args['host'], args['spool-path']),
        ]
        completed_process = run(cmd, check=True)
    else:
        pass  # local


if __name__ == '__main__':
    enqueue_job()
