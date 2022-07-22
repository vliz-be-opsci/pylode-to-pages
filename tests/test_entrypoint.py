import sys
import os
from pathlib import Path
import logging
import pytest
import shutil
from dotenv import load_dotenv
sys.path.append(str(Path(__file__).parent.parent))
import entrypoint as ep
from assert_outcome import assert_result


log = logging.getLogger('tests')


def enable_test_logging():
    load_dotenv()
    if 'PYTEST_LOGCONF' in os.environ:
        logconf = os.environ['PYTEST_LOGCONF']
        ep.enable_logging(logconf)
        log.info(f"Logging enabled according to config in {logconf}")


def run_single_test(testfile):
    sys.exit(pytest.main(["-v", "-s",  testfile]))


def test_main():
    enable_test_logging()
    log.info(
        f"Running tests in {__file__} " +
        "with -v(erbose) and -s(no stdout capturing) " +
        "and logging to stdout, level controlled by env var ${PYTEST_LOGCONF}")
    log.debug(f"argv == {sys.argv}")

    parent = Path(__file__).resolve().parent
    outfolder = parent / 'out'
    # clear outfolder
    shutil.rmtree(outfolder, ignore_errors=True)

    nsfolder = parent / 'ns-space'
    baseuri = 'https://example.org/pylode2pages-test'
    ontos = ep.publish_ontologies(baseuri, str(nsfolder), str(outfolder))

    log.info(f"ontologies produced == {ontos}")

    # assert returned list of ontologies processed.
    assert {'sub/onto-two.ttl', './onto-one.ttl'} == set(ontos.keys()), "unexpected set of processed ontologies in test"

    # assert outcome and available files
    assert_result(baseuri, outfolder, ontos)


if __name__ == '__main__':
    run_single_test(__file__)
