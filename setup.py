from setuptools import setup, find_packages
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='mri_meta_extract',

    version='1.0.0',

    description='Extract meta-data from DICOM and NIFTI files',
    long_description=long_description,

    author='Mirco Nasuti',
    author_email='mirco.nasuti@chuv.ch',

    license='Apache 2.0',

    classifiers=[
        'Development Status :: 5 - Stable',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python3',
    ],

    packages=['mri_meta_extract'],

    extras_require={
        'test': ['unittest'],
    },

    install_requires=['airflow', 'pydicom', 'sqlalchemy']
)
