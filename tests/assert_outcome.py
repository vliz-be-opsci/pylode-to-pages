from pathlib import Path

def assert_result(baseuri, outfolder, ontos):
    outfolder = Path(outfolder).resolve()
    for nskey in ontos:
        assert nskey.endswith('.ttl'), "processed ontology {nskey} should have .ttl extension"
        assert (outfolder / nskey).resolve().exists(), "the processed ontology {nskey} should be in the output folder"
        htmlpath = nskey.replace('.ttl', '.html')
        assert (outfolder / htmlpath).resolve().exists(), "the pylode generated html {nskey} should be in the output folder"
        # TODO some extra assertions: 
        # assert backups 
        # assert replacement of {{baseurl}} and {{name}}

    # TODO some general assertions
    # e.g. about the index.html
