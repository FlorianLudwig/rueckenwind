from setuptools import setup, find_packages

setup(
    name="rueckenwind",
    version="0.0.1",
    install_requires=['tornado>=2.2.1', 'jinja2', 'werkzeug==0.6.2', 'babel'],
    packages=find_packages(exclude=["test"]),
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'rw = rw.cli:main',
        ],
    }
)
