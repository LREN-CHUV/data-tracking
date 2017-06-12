from nose.tools import assert_equal

from data_tracking import files_recording
from data_tracking import connection

import os

if 'DB_URL' in os.environ:
    DB_URL = os.environ['DB_URL']
else:
    DB_URL = 'postgresql://postgres:postgres@localhost:5433/postgres'


class TestFilesRecording:

    def __init__(self):
        self.db_conn = None

    @classmethod
    def setup_class(cls):
        pass

    @classmethod
    def teardown_class(cls):
        pass

    def setup(self):
        self.db_conn = connection.Connection(DB_URL)

    def teardown(self):
        self.db_conn.close()

    def test_01_visit(self):
        """
        This is a basic use case.
        First, we want to visit a DICOM data-set after the 'ACQUISITION' process. Then, we want to visit a NIFTI
        data-set generated from the previous DICOM files after the 'DICOM2NIFTI' process.
        """

        # Create a simple provenance
        provenance_id = files_recording.create_provenance('TEST_DATA', db_url=DB_URL)
        assert_equal(self.db_conn.db_session.query(self.db_conn.Provenance).filter_by(
            dataset='TEST_DATA', matlab_version=None).count(), 1)

        # Visit DICOM files
        acquisition_step_id = files_recording.visit('./data/dcm/', provenance_id, 'ACQUISITION',
                                                    config=['sid_by_patient', 'pid_in_vid'], db_url=DB_URL)
        assert_equal(self.db_conn.db_session.query(self.db_conn.DataFile).filter_by(
            processing_step_id=acquisition_step_id).count(), 4)

        # Create a provenance with some fake Matlab and SPM version numbers
        provenance_id2 = files_recording.create_provenance('TEST_DATA',
                                                           software_versions={
                                                               'matlab_version': '2016R', 'spm_version': 'v12'},
                                                           db_url=DB_URL)
        assert_equal(self.db_conn.db_session.query(self.db_conn.Provenance).filter_by(
            dataset='TEST_DATA', matlab_version='2016R').count(), 1)

        assert_equal(self.db_conn.db_session.query(self.db_conn.DataFile).filter_by(
            type='DICOM', processing_step_id=acquisition_step_id).count(), 3)
        assert_equal(self.db_conn.db_session.query(self.db_conn.DataFile).filter_by(
            type='NIFTI', processing_step_id=acquisition_step_id).count(), 0)
        assert_equal(self.db_conn.db_session.query(self.db_conn.DataFile).filter_by(
            type='other', processing_step_id=acquisition_step_id).count(), 1)

        # Visit NIFTI files
        acquisition_step_id2 = files_recording.visit('./data/nii/', provenance_id2, 'DICOM2NIFTI', acquisition_step_id,
                                                     config=['sid_by_patient', 'pid_in_vid'], db_url=DB_URL)
        assert_equal(self.db_conn.db_session.query(self.db_conn.DataFile).filter_by(
            processing_step_id=acquisition_step_id2).count(), 3)

        assert_equal(self.db_conn.db_session.query(self.db_conn.DataFile).filter_by(
            type='DICOM', processing_step_id=acquisition_step_id2).count(), 0)
        assert_equal(self.db_conn.db_session.query(self.db_conn.DataFile).filter_by(
            type='NIFTI', processing_step_id=acquisition_step_id2).count(), 3)
        assert_equal(self.db_conn.db_session.query(self.db_conn.DataFile).filter_by(
            type='other', processing_step_id=acquisition_step_id2).count(), 0)

    def test_02_visit_again(self):
        """
        Here, run again the test_01_visit so we can check that there are no duplicates in the DB.
        """

        # Create a simple provenance
        provenance_id = files_recording.create_provenance('TEST_DATA', db_url=DB_URL)
        assert_equal(self.db_conn.db_session.query(self.db_conn.Provenance).filter_by(dataset='TEST_DATA').count(), 2)

        # Visit DICOM files
        acquisition_step_id = files_recording.visit('./data/dcm/', provenance_id, 'ACQUISITION',
                                                    config=['sid_by_patient', 'pid_in_vid'], db_url=DB_URL)
        assert_equal(self.db_conn.db_session.query(self.db_conn.DataFile).filter_by(
            processing_step_id=acquisition_step_id).count(), 4)

        # Create a provenance with some fake Matlab and SPM version numbers
        provenance_id2 = files_recording.create_provenance('TEST_DATA',
                                                           software_versions={
                                                               'matlab_version': '2016R', 'spm_version': 'v12'},
                                                           db_url=DB_URL)
        assert_equal(self.db_conn.db_session.query(self.db_conn.Provenance).filter_by(
            dataset='TEST_DATA', matlab_version='2016R').count(), 1)

        assert_equal(self.db_conn.db_session.query(self.db_conn.DataFile).filter_by(
            type='DICOM', processing_step_id=acquisition_step_id).count(), 3)
        assert_equal(self.db_conn.db_session.query(self.db_conn.DataFile).filter_by(
            type='NIFTI', processing_step_id=acquisition_step_id).count(), 0)
        assert_equal(self.db_conn.db_session.query(self.db_conn.DataFile).filter_by(
            type='other', processing_step_id=acquisition_step_id).count(), 1)

        # Visit NIFTI files
        acquisition_step_id2 = files_recording.visit('./data/nii/', provenance_id2, 'DICOM2NIFTI', acquisition_step_id,
                                                     config=['sid_by_patient', 'pid_in_vid'], db_url=DB_URL)
        assert_equal(self.db_conn.db_session.query(self.db_conn.DataFile).filter_by(
            processing_step_id=acquisition_step_id2).count(), 3)

        assert_equal(self.db_conn.db_session.query(self.db_conn.DataFile).filter_by(
            type='DICOM', processing_step_id=acquisition_step_id2).count(), 0)
        assert_equal(self.db_conn.db_session.query(self.db_conn.DataFile).filter_by(
            type='NIFTI', processing_step_id=acquisition_step_id2).count(), 3)
        assert_equal(self.db_conn.db_session.query(self.db_conn.DataFile).filter_by(
            type='other', processing_step_id=acquisition_step_id2).count(), 0)

    def test_03_visit_special(self):
        """
        This test tries to visit special files.
        These can be copies from already loaded files, DICOM with missing fields, etc.
        """
        # Create a simple provenance
        provenance_id = files_recording.create_provenance('TEST_DATA2', db_url=DB_URL)
        assert_equal(self.db_conn.db_session.query(self.db_conn.Provenance).filter_by(dataset='TEST_DATA2').count(), 1)

        # Visit various files
        acquisition_step_id = files_recording.visit('./data/any/', provenance_id, 'SPECIAL', 1, db_url=DB_URL)
        assert_equal(self.db_conn.db_session.query(self.db_conn.DataFile).filter_by(
            processing_step_id=acquisition_step_id).count(), 1)

        # A few more things to check
        assert_equal(self.db_conn.db_session.query(self.db_conn.DataFile).filter_by(
            type='DICOM', processing_step_id=acquisition_step_id).count(), 1)
        assert_equal(self.db_conn.db_session.query(self.db_conn.DataFile).filter_by(
            type='NIFTI', processing_step_id=acquisition_step_id).count(), 0)
        assert_equal(self.db_conn.db_session.query(self.db_conn.DataFile).filter_by(
            is_copy=True, processing_step_id=acquisition_step_id).count(), 1)
