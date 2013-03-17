from setuptools import setup, find_packages

setup(
    name="rueckenwind",
    version="0.0.1",
    install_requires=['tornado>=2.2.1', 'jinja2', 'werkzeug==0.6.2', 'babel', 'mock', 'configobj'],
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
