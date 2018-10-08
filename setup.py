
from setuptools import setup, find_packages
from odbt.core.version import get_version

VERSION = get_version()

f = open('README.md', 'r')
LONG_DESCRIPTION = f.read()
f.close()

setup(
    name='odbt',
    version=VERSION,
    description='Use Octopart to update and add componenta to an Altium DBlib',
    long_description=LONG_DESCRIPTION,
    long_description_content_type='text/markdown',
    author='Peter Oostewechel',
    author_email='peter_oostewechel@hotmail.com',
    url='https://github.com/peeter123/odbt',
    license='unlicensed',
    packages=find_packages(exclude=['ez_setup', 'tests*']),
    package_data={'odbt': ['templates/*']},
    include_package_data=True,
    entry_points="""
        [console_scripts]
        odbt = odbt.main:main
    """,
)
