#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os

from setuptools import setup, find_packages
import setuptools.command.test

BASE_PATH = os.path.abspath(os.path.dirname(__file__))
version_suffix = ''


with open('README.rst') as readme_file:
    readme = readme_file.read()

setup(
    name='rueckenwind',
    version='0.5.3',
    url='https://github.com/FlorianLudwig/rueckenwind',
    description='tornado based webframework',
    long_description=readme,
    author='Florian Ludwig',
    author_email='vierzigundzwei@gmail.com',
    install_requires=['tornado>=4.0.0,<5.0',
                      'jinja2',
                      'babel',
                      'argcomplete>=0.6.6,<1.0',
                      'configobj',
                      'chardet',
                      'pytz',
                      'PyYAML>=3.10',
                      'future'
                      ],
    extras_requires={
        'test': ['pytest', 'pep8'],
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
    license="http://www.apache.org/licenses/LICENSE-2.0",
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
    ],
)
