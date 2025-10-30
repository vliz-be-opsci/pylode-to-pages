import sys
import os
from pathlib import Path
import logging
import pytest
import shutil
from dotenv import load_dotenv
from assert_outcome import assert_result

sys.path.append(str(Path(__file__).parent.parent))
import entrypoint as ep


log = logging.getLogger("tests")


def enable_test_logging():
    load_dotenv()
    if "PYTEST_LOGCONF" in os.environ:
        logconf = os.environ["PYTEST_LOGCONF"]
        ep.enable_logging(logconf)
        log.info(f"Logging enabled according to config in {logconf}")


def run_single_test(testfile):
    sys.exit(pytest.main(["-v", "-s", testfile]))


def test_main():
    enable_test_logging()
    log.info(
        f"Running tests in {__file__} "
        + "with -v(erbose) and -s(no stdout capturing) "
        + "and logging to stdout, level controlled by env var ${PYTEST_LOGCONF}"
    )
    log.debug(f"argv == {sys.argv}")

    parent = Path(__file__).resolve().parent
    outfolder = parent / "out"
    # clear outfolder
    shutil.rmtree(outfolder, ignore_errors=True)

    nsfolder = parent / "ns-space"
    baseuri = "https://example.org/pylode2pages-test"
    ontos = ep.publish_ontologies(baseuri, str(nsfolder), str(outfolder), "templates")
    vocabs = ep.publish_vocabs(baseuri, str(nsfolder), str(outfolder), "templates")
    ep.publish_index_html(
        baseuri, str(nsfolder), str(outfolder), "templates", ontos, vocabs
    )
    log.info(f"ontologies produced == {ontos}")

    # assert returned list of ontologies processed.
    assert {"sub/onto-two.ttl", "./onto-one.ttl"} == set(
        ontos.keys()
    ), "unexpected set of processed ontologies in test"

    # assert outcome and available files
    assert_result(baseuri, outfolder, ontos)


def test_vocabs():
    enable_test_logging()
    log.info(
        f"Running tests in {__file__} "
        + "with -v(erbose) and -s(no stdout capturing) "
        + "and logging to stdout, level controlled by env var ${PYTEST_LOGCONF}"
    )
    parent = Path(__file__).resolve().parent
    outfolder = parent / "new_out"
    shutil.rmtree(outfolder, ignore_errors=True)
    nsfolder = parent / "new_in"

    baseuri = "https://example.org/pylode2pages-test"
    ontos = ep.publish_ontologies(baseuri, str(nsfolder), str(outfolder), "templates")
    vocabs = ep.publish_vocabs(baseuri, str(nsfolder), str(outfolder), "templates")
    ep.publish_index_html(
        baseuri, str(nsfolder), str(outfolder), "templates", ontos, vocabs
    )
    log.info(f"ontologies produced == {ontos}")


def test_ignore_folders():
    enable_test_logging()
    log.info("Testing ignore_folders functionality")
    parent = Path(__file__).resolve().parent
    outfolder = parent / "ignore-test-out"
    shutil.rmtree(outfolder, ignore_errors=True)
    nsfolder = parent / "ignore-test"

    baseuri = "https://example.org/pylode2pages-test"

    # Test with ignore_folders set to "should-ignore"
    ontos = ep.publish_ontologies(
        baseuri, str(nsfolder), str(outfolder), "templates", ignore_folders="should-ignore"
    )
    vocabs = ep.publish_vocabs(
        baseuri, str(nsfolder), str(outfolder), "templates", ignore_folders="should-ignore"
    )

    # Assert that only the should-process folder was processed
    log.info(f"ontologies produced == {ontos.keys()}")

    # Check that should-process/onto-one.ttl was processed
    assert any("should-process/onto-one.ttl" in key for key in ontos.keys()), \
        "should-process/onto-one.ttl should be processed"

    # Check that should-ignore/ignored-onto.ttl was NOT processed
    assert not any("should-ignore" in key for key in ontos.keys()), \
        "should-ignore folder should be ignored"

    log.info("ignore_folders test passed successfully")


def test_auto_camel_case():
    enable_test_logging()
    log.info("Testing auto_camel_case functionality")
    parent = Path(__file__).resolve().parent

    # Test with auto_camel_case enabled (default)
    outfolder_enabled = parent / "camel-case-enabled-out"
    shutil.rmtree(outfolder_enabled, ignore_errors=True)
    nsfolder = parent / "new_in"
    baseuri = "https://example.org/pylode2pages-test"

    vocabs_enabled = ep.publish_vocabs(
        baseuri, str(nsfolder), str(outfolder_enabled), "templates", auto_camel_case=True
    )
    log.info(f"vocabs produced with camelCase enabled == {vocabs_enabled.keys()}")

    # Check that the output file exists and contains camelCase IRIs
    vocab_html = outfolder_enabled / "test_quotes" / "test_quotes_vocab.html"
    if vocab_html.exists():
        with open(vocab_html, 'r') as f:
            content = f.read()
            # Should contain camelCase version: "testOne" instead of "Test One"
            assert "testOne" in content, "Should contain camelCase IRI fragment 'testOne'"
            log.info("Verified camelCase conversion: 'Test One' -> 'testOne'")

    # Test with auto_camel_case disabled
    outfolder_disabled = parent / "camel-case-disabled-out"
    shutil.rmtree(outfolder_disabled, ignore_errors=True)

    vocabs_disabled = ep.publish_vocabs(
        baseuri, str(nsfolder), str(outfolder_disabled), "templates", auto_camel_case=False
    )
    log.info(f"vocabs produced with camelCase disabled == {vocabs_disabled.keys()}")

    # Check that the output file contains original (non-camelCase) IRIs
    vocab_html_disabled = outfolder_disabled / "test_quotes" / "test_quotes_vocab.html"
    if vocab_html_disabled.exists():
        with open(vocab_html_disabled, 'r') as f:
            content = f.read()
            # Should NOT contain camelCase, should preserve original spacing
            assert "testOne" not in content, "Should NOT contain camelCase IRI fragment when disabled"
            log.info("Verified camelCase disabled: original IRI fragments preserved")

    log.info("auto_camel_case test passed successfully")


def test_csv_id_validation():
    enable_test_logging()
    log.info("Testing CSV ID validation functionality")

    # Test the validation function directly
    # Test case 1: Valid IDs
    valid_data = [
        {'ID': '1', 'PREFLABEL_EN': 'Test One'},
        {'ID': '2', 'PREFLABEL_EN': 'Test Two'},
        {'ID': '3', 'PREFLABEL_EN': 'Test Three'},
    ]
    validated, errors = ep.validate_csv_ids(valid_data, auto_camel_case=True)
    assert len(errors) == 0, "Should have no errors for valid unique IDs"
    assert len(validated) == 3, "Should have 3 validated rows"
    log.info("✓ Valid unique IDs passed")

    # Test case 2: Duplicate IDs
    duplicate_data = [
        {'ID': '1', 'PREFLABEL_EN': 'Test One'},
        {'ID': '1', 'PREFLABEL_EN': 'Test Two'},
    ]
    validated, errors = ep.validate_csv_ids(duplicate_data, auto_camel_case=True)
    assert len(errors) > 0, "Should have errors for duplicate IDs"
    assert any("Duplicate ID" in err for err in errors), "Should specifically report duplicate IDs"
    log.info(f"✓ Duplicate IDs detected: {errors}")

    # Test case 3: Non-URI-compliant IDs that get normalized
    non_compliant_data = [
        {'ID': '', 'PREFLABEL_EN': 'Test One'},  # Empty ID, use PREFLABEL_EN
        {'ID': '', 'PREFLABEL_EN': 'Test Two'},
    ]
    validated, errors = ep.validate_csv_ids(non_compliant_data, auto_camel_case=True)
    assert len(validated) == 2, "Should normalize non-compliant IDs when auto_camel_case=True"
    assert validated[0]['fragment_id'] == 'testOne', "Should convert 'Test One' to 'testOne'"
    log.info(f"✓ Non-compliant IDs normalized: {validated[0]['fragment_id']}")

    # Test case 4: URI-compliant IDs from full URIs
    uri_data = [
        {'ID': 'https://example.org/ns#concept1', 'PREFLABEL_EN': 'Concept One'},
        {'ID': 'https://example.org/ns#concept2', 'PREFLABEL_EN': 'Concept Two'},
    ]
    validated, errors = ep.validate_csv_ids(uri_data, auto_camel_case=True)
    assert len(errors) == 0, "Should handle full URIs correctly"
    assert validated[0]['fragment_id'] == 'concept1', "Should extract fragment from full URI"
    assert validated[1]['fragment_id'] == 'concept2', "Should extract fragment from full URI"
    log.info("✓ Full URI IDs handled correctly")

    log.info("CSV ID validation test passed successfully")


if __name__ == "__main__":
    run_single_test(__file__)
