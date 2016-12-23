|License|

MRI Meta-data Extractor
=======================

This is a Python library providing methods to extract meta-data from
DICOM files and folder tree containing

Build
-----

Run the ``python setup.py bdist`` script.

Install
-------

Run the ``pip install mri-meta-extract`` script.

Test
----

(You need Docker !)

Run ``test.sh``

Use
---

You can use the following functions:

-  ``dicom_import.dicom2db(folder)`` to scan the ``folder`` folder
   containing DICOM files and store their meta-data into the database.

-  ``dicom_import.visit_info(folder)`` to get the participant\_id and
   scan\_date meta-data from the ``folder`` folder (n.b. the folder must
   not mix different participants).

-  ``nifti_import.nifti2db(folder, participant_id, scan_date)`` to scan
   the ``folder`` folder containing NIFTI files and store the
   information contained in the files names into the DB. It links it to
   the participant and scan tables based on ``participant_id`` and
   ``scan_date`` parameters.

.. |License| image:: https://img.shields.io/badge/license-Apache--2.0-blue.svg
   :target: https://github.com/LREN-CHUV/airflow-imaging-plugins/blob/master/LICENSE