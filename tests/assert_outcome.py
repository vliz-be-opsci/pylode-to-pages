from pathlib import Path

def assert_result(baseuri, outfolder, ontos):
    outfolder = Path(outfolder).resolve()
    for o in ontos:
        assert o.endswith('.ttl'), "processed ontology {o} should have .ttl extension"
        assert (outfolder / o).resolve().exists(), "the processed ontology {o} should be in the output folder"
        h = o.replace('.ttl', '.html')
        assert (outfolder / h).resolve().exists(), "the pylode generated html {h} should be in the output folder"
        # todo some extra assertions
        # assert backups 
        # assert replacement of {{baseurl}} and {{name}}
