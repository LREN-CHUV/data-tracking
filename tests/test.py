import unittest
import sys
import os
import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from mri_meta_extract import dicom_import
from mri_meta_extract import nifti_import


class BasicTestSuite(unittest.TestCase):
    """Basic test suite"""

    def setUp(self):
        self.db_url = "postgresql://postgres:test@localhost:65432/postgres"
        self.dcm_folder = "./data/dcm/"
        self.nii_folder = "./data/nii/"
        self.pid = "PR00001"
        self.scan_date = datetime.datetime(2014, 7, 23, 0, 0)
        self.dcm_files_pattern = "**/MR.*"
        self.nii_files_pattern = "**/*.nii"

    def test_dicom_extract(self):
        assert dicom_import.visit_info(self.dcm_folder, self.dcm_files_pattern, self.db_url)[0] in [self.pid]
        assert dicom_import.visit_info(self.dcm_folder, self.dcm_files_pattern, self.db_url)[1] in [self.scan_date]
        dicom_import.dicom2db(self.dcm_folder, self.dcm_files_pattern, self.db_url)
        assert dicom_import.conn.db_session.query(dicom_import.conn.Participant).count() == 1

    def test_nifti_extract(self):
        nifti_import.nifti2db(self.nii_folder, self.pid, self.scan_date, self.nii_files_pattern, self.db_url)
        print(nifti_import.conn.db_session.query(nifti_import.conn.Nifti).count())
        assert nifti_import.conn.db_session.query(nifti_import.conn.Nifti).count() == 2

if __name__ == '__main__':
    unittest.main()
