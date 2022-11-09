from getpass import getpass
import logging
import sys

from .. import runner

def main():
    sudo_pass = getpass("Enter password to run sudo commands: ")
    try:
        r = runner.Runner(sudo_password=sudo_pass, debug=True, implementations_file_path="implementations.json")
        r.load_test_from_file("test_run.json")
        r.run()
    except runner.VegvisirInvalidImplementationConfigurationException as e:
        logging.error("Vegvisir implementations configuration contains incorrect data, halting execution")
        logging.error(e)
        sys.exit(1)
    except runner.VegvisirInvalidTestConfigurationException as e:
        logging.error("Vegvisir test configuration contains incorrect data, halting execution")
        logging.error(e)