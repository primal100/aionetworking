import os

from unittest import TestCase


class BaseTestCase(TestCase):
    base_home = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests", "data")

    def assertPathEqual(self, expected, actual):
        self.assertEqual(os.path.normpath(expected), os.path.normpath(actual))

    def assertPathExists(self, path):
        self.assertTrue(os.path.exists(path))

    def assertFileContentsEqual(self, file_path, expected_contents, mode='r'):
        self.assertPathExists(file_path)
        with open(file_path, mode) as f:
            actual_contents = f.read()
            self.assertEqual(actual_contents, expected_contents)

    def assertBinaryFileContentsEqual(self, file_path, expected_contents):
        self.assertPathExists(file_path)
        self.assertFileContentsEqual(file_path, expected_contents, mode='rb')