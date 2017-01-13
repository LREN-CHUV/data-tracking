import sys
import os
import subprocess

from nose.tools import assert_equal
from nose.tools import assert_not_equal

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from mri_meta_extract import files_recording


class TestAll(object):
    def __init__(self):
        self.db_url = None
        subprocess.call("./init_db.sh", shell=True)

    def setup(self):
        """This method is run once before _each_ test method is executed"""
        self.db_url = 'postgresql://postgres:postgres@localhost:5432/postgres'

    def test_(self):
        provenance_id = files_recording.create_provenance('TEST LREN DATA')
        files_recording.visit('./data/dcm/', provenance_id, db_url=self.db_url)
