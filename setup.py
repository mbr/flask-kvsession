import os
import sys

from setuptools import setup

if sys.version_info < (2, 7):
    tests_require = ['unittest2']
    test_suite = 'unittest2.collector'
else:
    tests_require = []
    test_suite = 'unittest.collector'


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name='Flask-KVSession',
    version='0.1',
    url='https://github.com/mbr',
    license='MIT',
    author='Marc Brinkmann',
    author_email='git@marcbrinkmann.de',
    description='Transparent server-side session support for flask',
    long_description=read('README.rst'),
    packages=['flaskext', 'tests'],
    namespace_packages=['flaskext'],
    zip_safe=False,
    platforms='any',
    install_requires=[
        'Flask', 'simplekv'
    ],
    tests_require=tests_require,
    test_suite='unittest2.collector',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ]
)
