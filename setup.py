# -*- coding: utf-8 -*-
from distutils.command.sdist import sdist
from setuptools import setup, find_packages


class sdist_git(sdist):
    user_options = sdist.user_options + [
        ('dev', None, "Add a dev marker")
    ]

    def initialize_options(self):
        sdist.initialize_options(self)
        self.dev = 0

    def run(self):
        if self.dev:
            suffix = ".git{}".format(self.get_last_committed_date())
            self.distribution.metadata.version += suffix
        sdist.run(self)

    def get_last_committed_date(self):
        from git import Repo
        from datetime import datetime
        repo = Repo()
        committed_date = repo.head.commit.committed_date
        return datetime.fromtimestamp(committed_date).strftime('%Y%m%d%H%M%S')


setup(
    name="rueckenwind",
    version="0.0.1",
    # use fix versions of motor und PyMongo for now, see:
    # https://groups.google.com/forum/?hl=de&fromgroups=#!topic/python-tornado/xEpZ_NU5eDE
    install_requires=['tornado>=3.0.1,<4.0', 'jinja2', 'werkzeug==0.6.2', 'babel', 'mock', 'configobj',
                      'motor==0.1', 'PyMongo==2.5.0'],
    packages=find_packages(),
    include_package_data=True,
    package_data={
        'rw': ['*.html', '*.css', 'templates/html5', 'templates/form']
    },
    entry_points={
        'console_scripts': [
            'rw = rw.cli:main',
        ],
    },
    cmdclass={'sdist': sdist_git}
)
