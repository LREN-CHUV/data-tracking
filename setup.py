from setuptools import setup
from os import path
import codecs

here = path.abspath(path.dirname(__file__))

with codecs.open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='data-tracking',
    version='1.5.14',
    zip_safe=False,
    url='https://github.com/LREN-CHUV/data-tracking',
    description='Extract meta-data from DICOM and NIFTI files',
    long_description=long_description,
    author='Mirco Nasuti',
    author_email='mirco.nasuti@chuv.ch',
    license='Apache 2.0',
    packages=['data_tracking'],
    keywords='mri dicom nifti',
    install_requires=[
        'apache-airflow>=1.8.1',
        'pydicom>=0.9.9',
        'SQLAlchemy>=1.1.6',
        'python-magic>=0.4.12',
        'nibabel>=2.1.0',
        'psycopg2>=2.7.1'],
    classifiers=(
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'Operating System :: Unix',
        'License :: OSI Approved :: Apache Software License',
        'Topic :: Scientific/Engineering :: Bio-Informatics',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    )
)
