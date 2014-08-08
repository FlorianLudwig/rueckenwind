# -*- coding: utf-8 -*-
import sys

from distutils.command.sdist import sdist
from setuptools import setup, find_packages
from setuptools.command.test import test as TestCommand


version_suffix = ''


class Tox(TestCommand):
    def finalize_options(self):
        TestCommand.finalize_options(self)
        # self.test_args = ["-v", "-epy"]
        self.test_suite = True

    def run_tests(self):
        import tox
        tox.cmdline(self.test_args)


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
        'test': ['tox', 'pytest'],
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
    cmdclass={'sdist': sdist_git}
)
