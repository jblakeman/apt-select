"""A setuptools based setup module.
See:
https://packaging.python.org/en/latest/distributing.html """

from setuptools import setup, find_packages
from codecs import open
from os import path
from apt_select import __version__

here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='apt-select',
    version=__version__,
    description='Ubuntu Archive Mirror reporting tool for apt sources configuration',
    long_description=long_description,
    url='https://github.com/jblakeman/apt-select',
    author='John Blakeman',
    author_email='john@johnblakeman.com',
    license='MIT',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: MIT License',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Topic :: System :: Installation/Setup',
        'Topic :: System :: Networking',
        'Topic :: System :: Software Distribution',
        'Topic :: System :: Systems Administration',
        'Topic :: Utilities',
    ],
    keywords='latency status rank reporting apt configuration',
    packages=find_packages(exclude=['tests']),
    install_requires=['requests', 'beautifulsoup4'],
    entry_points = {
        'console_scripts': [
            'apt-select = apt_select.__main__:main'
        ]
    }
)
