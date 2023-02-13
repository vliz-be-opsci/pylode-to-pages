import sys
import os
from pathlib import Path
import shutil
sys.path.append(str(Path(__file__).parent.parent))
import entrypoint as ep

print(f"Running tests in {__file__} ")
parent = Path(__file__).resolve().parent
outfolder = parent / 'new_out'
shutil.rmtree(outfolder, ignore_errors=True)
nsfolder = parent / 'new_in'
baseuri = 'https://example.org/pylode2pages-test'
ontos = ep.publish_ontologies(baseuri, str(nsfolder), str(outfolder))
vocabs = ep.publish_vocabs(baseuri, str(nsfolder), str(outfolder))
ep.publish_combined_index(baseuri, str(nsfolder), str(outfolder))