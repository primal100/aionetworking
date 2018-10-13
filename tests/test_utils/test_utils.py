from unittest import TestCase
from lib import utils

class UtilsTestCase(TestCase):
    def test_adapt_domain(self):
        result = utils.adapt_domain()
        self.assertEqual(result, "")

    def timestamp_to_readable_string(self):
        result = utils.timestamp_to_utc_string()
        self.assertEqual(result, "")