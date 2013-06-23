from setuptools import setup, find_packages

setup(
    name="rueckenwind",
    version="0.0.1",
    # use fix versions of motor und PyMongo for now, see:
    # https://groups.google.com/forum/?hl=de&fromgroups=#!topic/python-tornado/xEpZ_NU5eDE
    install_requires=['tornado>=3.0.1,<4.0', 'jinja2', 'werkzeug==0.6.2', 'babel', 'mock', 'configobj', 'motor==0.1', 'PyMongo==2.5.0'],
    packages=find_packages(exclude=["test"]),
    include_package_data=True,
    package_data={
        'rw': ['*.html', '*.css', 'templates/html5']
    },
    entry_points={
        'console_scripts': [
            'rw = rw.cli:main',
        ],
    }
)
