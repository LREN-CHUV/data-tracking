[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](https://github.com/LREN-CHUV/airflow-imaging-plugins/blob/master/LICENSE) [![Codacy Badge](https://api.codacy.com/project/badge/Grade/4547fb5d1e464e4087640e046893576a)](https://www.codacy.com/app/mirco-nasuti/mri-meta-extract?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=LREN-CHUV/mri-meta-extract&amp;utm_campaign=Badge_Grade) [![CircleCI](https://circleci.com/gh/LREN-CHUV/mri-meta-extract.svg?style=svg)](https://circleci.com/gh/LREN-CHUV/mri-meta-extract)

# MRI Meta-data Extractor

This is a Python library providing methods to scan folders, extract meta-data from files (DICOM, NIFTI, ...) and store 
them in a database.

## Build

Run `./build.sh`. (Builds for Python3)

## Publish on PyPi

Run `./publish.sh`.

## Install

Run `pip install mri-meta-extract`. (Only tested with Python3)

## Test

Enter the `tests` directory.

### With Docker

Run `test.sh`

### Without Docker

* Run a Postgres database on `localhost:5432`.
* Run `nosetest unittest.py`

## Use

Create a provenance entity using :
   
    create_provenance(dataset, matlab_version=None, spm_version=None, spm_revision=None, fn_called=None, fn_version=None, others=None, db_url=None)
    
    Create (or get if already exists) a provenance entity, store it in the database and get back a provenance ID.
    * param dataset: Name of the data set.
    * param matlab_version: (optional) Matlab version.
    * param spm_version: (optional) SPM version.
    * param spm_revision: (optional) SPM revision.
    * param fn_called: (optional) Function called.
    * param fn_version: (optional) Function version.
    * param others: (optional) Any other information can be set using this field.
    * param db_url: (optional) Database URL. If not defined, it looks for an Airflow configuration file.
    * return: Provenance ID.
    
Scan a folder to populate the database :

    def visit(folder, provenance_id, previous_step_id=None, db_url=None)
    
    Record all files from a folder into the database.
    The files are listed in the DB. If a file has been copied from previous step without any transformation, it will be
    detected and marked in the DB. The type of file will be detected and stored in the DB. If a files (e.g. a DICOM
    file) contains some meta-data, those will be stored in the DB.
    * param folder: folder path.
    * param provenance_id: provenance label.
    * param previous_step_id: (optional) previous processing step ID. If not defined, we assume this is the first
    processing step.
    * param db_url: (optional) Database URL. If not defined, it looks for an Airflow configuration file.
    * return: return processing step ID.
    
