import sys
import os
import subprocess

from nose.tools import assert_equal

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from mri_meta_extract import files_recording
from mri_meta_extract import connection


class TestAll:

    def __init__(self):
        self.db_url = None
        self.db_conn = None
        self.db_url = 'postgresql://postgres:postgres@localhost:5432/postgres'

    @classmethod
    def setup_class(cls):
        subprocess.call("./init_db.sh", shell=True)

    @classmethod
    def teardown_class(cls):
        pass

    def setup(self):
        """This method is run once before _each_ test method is executed"""
        self.db_conn = connection.Connection(self.db_url)

    def teardown(self):
        self.db_conn.close()

    def test_all(self):
        provenance_id = files_recording.create_provenance('LREN', db_url=self.db_url)
        files_recording.visit('./data/dcm/', provenance_id, db_url=self.db_url)
        files_recording.visit('./data/nii/', provenance_id, db_url=self.db_url)
        assert_equal(self.db_conn.db_session.query(self.db_conn.Provenance).count(), 1)
