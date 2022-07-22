from assert_outcome import
from tests.assert_outcome import assert_result 

def test_integration_run_result():
    assert_result("http://example.org/integration-test", "tests/out", {"sub/onto-two.ttl", "onto-one.ttl"})
