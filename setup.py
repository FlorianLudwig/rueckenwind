# -*- coding: utf-8 -*-
from distutils.command.sdist import sdist
from setuptools import setup, find_packages
import sys


setup(
    name="rueckenwind",
    version="0.3.1",
    url='https://github.com/FlorianLudwig/rueckenwind',
    description='tornado based webframework',
    author='Florian Ludwig',
    # use fix versions of motor und PyMongo for now, see:
    # https://groups.google.com/forum/?hl=de&fromgroups=#!topic/python-tornado/xEpZ_NU5eDE
    install_requires=['tornado>=3.0.1,<4.0', 'jinja2', 'werkzeug==0.6.2', 'babel', 'mock', 'configobj', 'chardet',
                      'motor==0.1.1', 'PyMongo==2.5.0', 'pytz', 'argcomplete>=0.6.6,<1.0'],
    packages=find_packages(exclude=['*.test', '*.test.*']),
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'rw = rw.cli:main',
        ],
    }
)
