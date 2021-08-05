import sys

from vegvisir.runner import Runner

def main():
	runner = Runner()

	return runner.run()

if __name__ == "__main__":
    sys.exit(main())