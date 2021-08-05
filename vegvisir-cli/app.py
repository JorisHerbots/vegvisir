import sys

from vegvisir.runner import Runner


def main():
    runner = Runner(debug=True)

    return runner.run()


if __name__ == "__main__":
    sys.exit(main())
