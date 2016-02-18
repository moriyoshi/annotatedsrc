# -*- coding: utf-8 -*-
import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.rst')).read()
CHANGES = open(os.path.join(here, 'CHANGES.txt')).read()

requires = [
    'pygments',
    'pyramid',
    'gunicorn',
    'future',
    'gitpython',
    ]

setup(name='embedsrc',
      version='0.0',
      use_date_versioning=True,
      description='embedsrc',
      long_description=README + '\n\n' + CHANGES,
      classifiers=[
        "Programming Language :: Python",
        "Framework :: Pylons",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
        ],
      author='',
      author_email='',
      url='',
      keywords='',
      package_dir={'': 'src'},
      packages=find_packages('src'),
      include_package_data=True,
      zip_safe=False,
      install_requires=requires,
      #setup_requires=[],
      #tests_require=tests_require,
      #extras_require=extras_require,
      test_suite="embedsrc",
      entry_points="""\
      [paste.app_factory]
      main = embedsrc:paster_main
      """,
      paster_plugins=['pyramid'],
      )

