import sys
import os
import subprocess

from nose.tools import assert_equal

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from mri_meta_extract import files_recording
from mri_meta_extract import connection


DB_URL = 'postgresql://postgres:postgres@localhost:5432/postgres'


class TestFilesRecording:

    def __init__(self):
        self.db_conn = None

    @classmethod
    def setup_class(cls):
        subprocess.call("./init_db.sh", shell=True)  # Create the DB tables

    @classmethod
    def teardown_class(cls):
        pass

    def setup(self):
        self.db_conn = connection.Connection(DB_URL)

    def teardown(self):
        self.db_conn.close()

    def test_visit(self):
        # Create a simple provenance
        provenance_id = files_recording.create_provenance('TEST_DATA', db_url=DB_URL)
        assert_equal(self.db_conn.db_session.query(self.db_conn.Provenance).count(), 1)

        # Visit DICOM files
        acquisition_step_id = files_recording.visit(
            'ACQUISITION', './data/dcm/', provenance_id, db_url=DB_URL)
        assert_equal(self.db_conn.db_session.query(self.db_conn.DataFile).count(), 3)

        # Create a provenance with some fake Matlab and SPM version numbers
        provenance_id = files_recording.create_provenance(
            'TEST_DATA', matlab_version='2016R', spm_version='v12', db_url=DB_URL)
        assert_equal(self.db_conn.db_session.query(self.db_conn.Provenance).count(), 2)

        # Visit NIFTI files
        files_recording.visit(
            'DICOM2NIFTI', './data/nii/', provenance_id, previous_step_id=acquisition_step_id, db_url=DB_URL)
        assert_equal(self.db_conn.db_session.query(self.db_conn.DataFile).count(), 6)

        # A few more things to check
        assert_equal(self.db_conn.db_session.query(self.db_conn.DataFile).filter_by(type='DICOM').count(), 3)
        assert_equal(self.db_conn.db_session.query(self.db_conn.DataFile).filter_by(type='NIFTI').count(), 3)
