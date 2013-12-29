#!/usr/bin/env python
"""
This is a simple script to backup a database and a set of files into a single
archive, encrypt it and store it on S3.
"""
from __future__ import print_function

import argparse
import datetime
import logging
import os
import shutil
import subprocess
import sys
import tempdir
import urlparse
import yaml

from boto.s3.connection import S3Connection
from boto.s3.key import Key


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config-file', default='backup.yml')
    parser.add_argument('--output-dir', default=None)
    parser.add_argument('--upload', default=False, action='store_true')
    parser.add_argument('--quiet', default=False, action='store_true')
    parser.add_argument('--debug', default=False, action='store_true')
    opts = parser.parse_args()

    if not os.path.exists(opts.config_file):
        sys.exit("The specified config file does not exist!")

    if not opts.quiet:
        if opts.debug:
            logging.basicConfig(level=logging.DEBUG)
        else:
            logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.ERROR)

    config = None

    if opts.output_dir:
        opts.output_dir = os.path.abspath(opts.output_dir)

    with open(opts.config_file) as fp:
        logging.debug("Loading config from {0}".format(opts.config_file))
        config = yaml.safe_load(fp)
    config['quiet'] = opts.quiet

    with tempdir.in_tempdir() as dir_path:
        logging.debug("Chdir to {0}".format(dir_path))
        backup_folder = datetime.datetime.utcnow().strftime(
            config['output_prefix'])
        logging.info("Creating backup folder: {0}".format(backup_folder))
        os.mkdir(backup_folder, 0o700)
        os.chdir(backup_folder)

        _backup_db(config)
        _backup_files(config)

        logging.debug("Chdir to {0}".format(dir_path))
        os.chdir(dir_path)
        archive_name = _create_archive(backup_folder, config)
        enc_archive_name = _encrypt_file(archive_name, config)
        if opts.upload:
            _upload_file(enc_archive_name, config)
        if opts.output_dir:
            shutil.move(enc_archive_name, opts.output_dir)


def _create_archive(folder, config):
    archive_name = folder + '.zip'
    subprocess.check_call(
        ['zip', '--quiet', '-r', archive_name, folder],
        env=os.environ)
    return archive_name


def _backup_db(config):
    env = {}
    env.update(os.environ)
    url = urlparse.urlparse(os.environ[config['database_env']])
    db_name = url.path.lstrip('/')
    cmd = ['pg_dump', '-w', '-f',
           '{0}.sql'.format(db_name)]
    if url.scheme != 'postgres':
        sys.exit("We only support postgres at this time!")
    cmd.append('-h')
    cmd.append(url.hostname)
    if url.username:
        cmd.append('-u')
        cmd.append(url.username)
    if url.password:
        env['PGPASSWORD'] = url.password
    cmd.append(db_name)
    subprocess.check_call(cmd, env=env)


def _encrypt_file(filename, config):
    result = filename + '.enc'
    env = {}
    env.update(os.environ)
    enc_method = config['encryption']['method']
    if enc_method == 'aes':
        env.update({'PASS': config['encryption']['password']})
        subprocess.check_call([
            'openssl', 'aes-256-cbc', '-in', filename,
            '-out', result, '-pass', 'env:PASS'], env=env)
    elif enc_method == 'gpg':
        subprocess.check_call([
            'gpg', '--output', result, '--recipient',
            config['encryption']['recipient'], '--encrypt', filename
            ])
    else:
        raise Exception("Unsupported encryption method")
    return result


def _backup_files(config):
    os.mkdir('files', 0o700)
    for folder_name, folder_path in config['files'].items():
        shutil.copytree(folder_path, os.path.join('files', folder_name))


def _upload_file(file, config):

    conn = S3Connection(config['aws']['access_key_id'],
                        config['aws']['access_key_secret'])
    bucket = conn.get_bucket(config['aws']['bucket'], validate=False)
    key = Key(bucket)
    key.key = file
    progress_callback = _report_progress
    if config['quiet']:
        progress_callback = lambda a, b: None
    key.set_contents_from_filename(file, encrypt_key=True,
                                   cb=progress_callback)
    if not config['quiet']:
        print("")


def _report_progress(uploaded_bytes, file_size):
    field_length = len(str(file_size))
    print("\r{0} / {1}".format(
        str(uploaded_bytes).rjust(field_length), file_size),
        end='')


if __name__ == '__main__':
    main()
