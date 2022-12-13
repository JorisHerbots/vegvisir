from getpass import getpass
import logging
import sys

from .. import runner

def main():
    # TODO jherbots: temporary file loading mechanism
    implementations_path = sys.argv[1] if len(sys.argv) >= 2 else "implementations.json"
    experiment_path = sys.argv[2] if len(sys.argv) >= 3 else  "experiment.json"

    print(f"Using implementations file: {implementations_path}")
    print(f"Using experiment file: {experiment_path}")
    sudo_pass = getpass("Enter password to run sudo commands: ")
    try:
        r = runner.Runner(sudo_password=sudo_pass, debug=True, implementations_file_path=implementations_path)
        r.load_experiment_from_file(experiment_path)
        # r.load_experiment_from_file("test_run2.json")
        # r.load_experiment_from_file("test_run.json")
        r.run()
    except runner.VegvisirInvalidImplementationConfigurationException as e:
        logging.error("Vegvisir implementations configuration contains incorrect data, halting execution")
        logging.error(e)
        sys.exit(1)
    except runner.VegvisirInvalidExperimentConfigurationException as e:
        logging.error("Vegvisir test configuration contains incorrect data, halting execution")
        logging.error(e)
        sys.exit(1)
    except runner.VegvisirException as e:
        logging.error("Generic Vegvisir error encountered, halting exception.")
        logging.error(e)
        sys.exit(1)
    # finally:
    #     sys.exit(0)