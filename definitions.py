import os

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
CONF_DIR = os.path.join(ROOT_DIR, 'conf')
LOGS_DIR = os.path.join(ROOT_DIR, 'logs')
DATA_DIR = os.path.join(ROOT_DIR, 'data')
SCRIPTS_DIR = os.path.join(ROOT_DIR, 'scripts')
TESTS_DIR = os.path.join(ROOT_DIR, 'tests')
TEST_CONF_DIR = os.path.join(TESTS_DIR, 'conf')
TEST_LOGS_DIR = os.path.join(TESTS_DIR, 'logs')
TEST_DATA_DIR = os.path.join(TESTS_DIR, 'data')
