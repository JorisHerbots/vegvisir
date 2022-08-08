import sys
from vegvisir.manager import Manager
from getpass import getpass

def main():
    sudo_pass = getpass("Enter password to run sudo commands: ")

    manager = Manager(sudo_pass)
    #runner = Runner(sudo_password=sudo_pass, debug=True)
    #runner.set_implementations_from_file("implementations.json")

    #return runner.run()


if __name__ == "__main__":
    sys.exit(main())
