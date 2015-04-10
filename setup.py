# -*- coding: utf-8 -*-
import os
import sys

from distutils.command.sdist import sdist
from setuptools import setup, find_packages
import setuptools.command.test

BASE_PATH = os.path.abspath(os.path.dirname(__file__))
version_suffix = ''


class TestCommand(setuptools.command.test.test):
    def finalize_options(self):
        setuptools.command.test.test.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        fails = []
        from tox._config import parseconfig
        from tox._cmdline import Session

        config = parseconfig(self.test_args, 'tox')
        retcode = Session(config).runcommand()
        if retcode != 0:
            fails.append('tox returned errors')

        import pep8
        style_guide = pep8.StyleGuide(config_file=BASE_PATH + '/.pep8')
        style_guide.input_dir(BASE_PATH + '/rw')
        if style_guide.options.report.get_count() != 0:
            fails.append('pep8 returned errros for rw/')

        style_guide = pep8.StyleGuide(config_file=BASE_PATH + '/.pep8')
        style_guide.input_dir(BASE_PATH + '/test')
        if style_guide.options.report.get_count() != 0:
            fails.append('pep8 returned errros for test/')

        if fails:
            print('\n'.join(fails))
            sys.exit(1)


def get_version_suffix():
    from git import Repo
    from datetime import datetime
    repo = Repo()
    committed_date = repo.head.commit.committed_date
    return '.git' + datetime.fromtimestamp(committed_date).strftime('%Y%m%d%H%M%S')


class sdist_git(sdist):
    def make_release_tree(self, base_dir, files):
        sdist.make_release_tree(self, base_dir, files)
        # make sure we include the git version in the release
        setup_py = open(base_dir + '/setup.py').read()
        setup_py = setup_py.replace("\nversion_suffix = ''\n", "\nversion_suffix = {}\n".format(repr(version_suffix)))
        f = open(base_dir + '/setup.py', 'w')
        f.write(setup_py)
        f.close()


if '--dev' in sys.argv:
    version_suffix = get_version_suffix()
    sys.argv.remove('--dev')


setup(
    name="rueckenwind",
    version="0.4.0" + version_suffix,
    url='https://github.com/FlorianLudwig/rueckenwind',
    description='tornado based webframework',
    author='Florian Ludwig',
    install_requires=['tornado>=4.0.0,<5.0',
                      'jinja2',
                      'babel',
                      'argcomplete>=0.6.6,<1.0',
                      'mock',
                      'configobj',
                      'chardet',
                      'pytz',
                      'PyYAML>=3.10',
                      'future'
                      ],
    extras_requires={
        'test': ['tox', 'pytest', 'pep8'],
        'docs': ['sphinx_rtd_theme']
    },
    packages=find_packages(exclude=['*.test', '*.test.*']),
    include_package_data=True,
    package_data={
        'rw': ['*.html', '*.css', 'templates/html5', 'templates/form', 'templates/nginx']
    },
    entry_points={
        'console_scripts': [
            'rw = rw.cli:main',
        ],
    },
    cmdclass={
        'sdist': sdist_git,
        'test': TestCommand
    },
    license="http://www.apache.org/licenses/LICENSE-2.0",
    classifiers=[
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
    ],
)
