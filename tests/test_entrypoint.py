import sys
import os
import logging
import pytest
from dotenv import load_dotenv

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import entrypoint as ep


log = logging.getLogger('tests')


def enable_test_logging():
    load_dotenv()
    if 'PYTEST_LOGCONF' in os.environ:
        logconf = os.environ['PYTEST_LOGCONF']
        ep.enable_logging(logconf)
        log.info(f"Logging enabled according to config in {logconf}")


def run_single_test(testfile):
    sys.exit(pytest.main(["-v", "-s",  testfile]))


def test_main() :
    enable_test_logging()
    log.info(
        f"Running tests in {__file__} " +
        "with -v(erbose) and -s(no stdout capturing) " +
        "and logging to stdout, level controlled by env var ${PYTEST_LOGCONF}")
    log.debug(f"argv == {sys.argv}")

    outfolder = os.path.join(os.path.dirname(__file__), '..', 'out')
    nsfolder = os.path.join(os.path.dirname(__file__), 'ns-space')
    baseuri = 'https://example.org/pylode2pages-test'
    ontos = ep.publish_ontologies(outfolder, nsfolder, baseuri)

    #todo assert produced output and returned list of ontologies processed.


if __name__ == '__main__':
    run_single_test(__file__)

