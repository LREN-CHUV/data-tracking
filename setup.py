from setuptools import setup
from os import path
import codecs

here = path.abspath(path.dirname(__file__))

with codecs.open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='mri_meta_extract',
    version='1.3.3',
    url='https://github.com/LREN-CHUV/mri-meta-extract',
    description='Extract meta-data from DICOM and NIFTI files',
    long_description=long_description,
    author='Mirco Nasuti',
    author_email='mirco.nasuti@chuv.ch',
    license='Apache 2.0',
    packages=['mri_meta_extract'],
    extras_require={
        'test': ['unittest'],
    },
    install_requires=['airflow', 'pydicom', 'sqlalchemy', 'nose', 'python-magic', 'nibabel', 'psycopg2']
)
