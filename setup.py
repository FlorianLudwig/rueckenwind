# -*- coding: utf-8 -*-
from distutils.command.sdist import sdist
from setuptools import setup, find_packages
import sys

version_suffix = ''


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
    version="0.0.1" + version_suffix,
    # use fix versions of motor und PyMongo for now, see:
    # https://groups.google.com/forum/?hl=de&fromgroups=#!topic/python-tornado/xEpZ_NU5eDE
    install_requires=['tornado>=3.0.1,<4.0', 'jinja2', 'werkzeug==0.6.2', 'babel', 'mock', 'configobj', 'chardet',
                      'motor==0.1.1', 'PyMongo==2.5.0'],
    packages=find_packages(),
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
