import sys
import os

from nose.tools import assert_equal
from nose.tools import assert_not_equal

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from mri_meta_extract import files_recording


class TestA(object):
    @classmethod
    def setup_class(klass):
        """This method is run once for each class before any tests are run"""

    @classmethod
    def teardown_class(klass):
        """This method is run once for each class _after_ all tests are run"""

    def setUp(self):
        """This method is run once before _each_ test method is executed"""

    def teardown(self):
        """This method is run once after _each_ test method is executed"""

    def test_init(self):
        assert_equal("Some Value", "Some Value")
        assert_not_equal("Correct Value", "Incorrect Value")

    def test_(self):
        assert_equal(True, True)
        assert_not_equal(True, False)
