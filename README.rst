|License| |Codacy Badge| |CircleCI|

MRI Meta-data Extractor
=======================

This is a Python library providing methods to scan folders, extract
meta-data from files (DICOM, NIFTI, ...) and store them in a database.

Install
-------

Run ``pip install mri-meta-extract``. (Only tested with Python3)

Use
---

Import the functions you need like this :
``from mri_meta_extract.files_recording import create_provenance, visit``.

Create a provenance entity using :

::

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

::

    def visit(step_name, folder, provenance_id, previous_step_id=None, boost=True, db_url=None)

    Record all files from a folder into the database.
    The files are listed in the DB. If a file has been copied from previous step without any transformation, it will be
    detected and marked in the DB. The type of file will be detected and stored in the DB. If a files (e.g. a DICOM
    file) contains some meta-data, those will be stored in the DB.
    * param step_name: Name of the processing step that produced the folder to visit.
    * param folder: folder path.
    * param provenance_id: provenance label.
    * param previous_step_id: (optional) previous processing step ID. If not defined, we assume this is the first
    processing step.
    * param boost: (optional) When enabled, we consider that all the files from a same folder share the same meta-data.
    When enabled, the processing is (about 2 times) faster. This option is enabled by default.
    * param db_url: (optional) Database URL. If not defined, it looks for an Airflow configuration file.
    * param sid_by_patient: Rarely, a data set might use study IDs which are unique by patient (not for the whole study).
    E.g.: LREN data. In such a case, you have to enable this flag. This will use PatientID + StudyID as a session ID.
    * return: return processing step ID.

Build
-----

Run ``./build.sh``. (Builds for Python3)

(This includes the auto-generation of the README.rst based on the
README.md)

Test
----

Enter the ``tests`` directory.

With Docker
~~~~~~~~~~~

Run ``test.sh``

Without Docker
~~~~~~~~~~~~~~

-  Run a Postgres database on ``localhost:5432``.
-  Run ``nosetest unittest.py``

Publish on PyPi
---------------

Run ``./publish.sh``.

(This builds the project prior to pushing on PyPi)

NOTE : Do not forget to update the version number in the setup.py prior
to publishing.

NOTES
-----

-  This project contains a reference to a Git submodule. You can use the
   ``--recursive`` flag when cloning the project to clone the submodule
   too.

.. |License| image:: https://img.shields.io/badge/license-Apache--2.0-blue.svg
   :target: https://github.com/LREN-CHUV/mri-meta-extract/blob/master/LICENSE
.. |Codacy Badge| image:: https://api.codacy.com/project/badge/Grade/4547fb5d1e464e4087640e046893576a
   :target: https://www.codacy.com/app/mirco-nasuti/mri-meta-extract?utm_source=github.com&utm_medium=referral&utm_content=LREN-CHUV/mri-meta-extract&utm_campaign=Badge_Grade
.. |CircleCI| image:: https://circleci.com/gh/LREN-CHUV/mri-meta-extract.svg?style=svg
   :target: https://circleci.com/gh/LREN-CHUV/mri-meta-extract
