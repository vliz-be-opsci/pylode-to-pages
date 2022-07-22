#!/usr/bin/env -S python3 -B

# NOTE: If you are using an alpine docker image
# such as pyaction-lite, the -S option above won't
# work. The above line works fine on other linux distributions
# such as debian, etc, so the above line will work fine
# if you use pyaction:4.0.0 or higher as your base docker image.

import sys
import os
import shutil
import logging
import logging.config
import yaml
from dotenv import load_dotenv
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from pylode import OntDoc, PylodeError, __version__ as plv


log = logging.getLogger('pylode2pages')


def enable_logging(logconf):
    if logconf is not None:
        if Path(logconf).is_file():
            with open(logconf, 'r') as yml_logconf:
                logging.config.dictConfig(yaml.load(yml_logconf, Loader=yaml.SafeLoader))
        else:
            sys.stderr.write(f"--warning-- log config file pointed to by {logconf} does not exist. No logging configured.")
            sys.stderr.flush()


def ontopub(baseuri, nsfolder, nssub, nsname, outfolder):
    log.debug(f"ontology to process: {nssub}/{nsname} in {nsfolder}")

    nsfolder = Path(nsfolder)
    outfolder = Path(outfolder)
    nspath = (nsfolder / nssub / nsname).resolve()
    outpath = (outfolder / nssub / nsname).resolve()
    outbackpath = (outfolder / nssub / f"{nsname}.bak").resolve()

    # extract name for {{ self }} from filename
    name = str(Path(nsname).stem)
    # produce html path
    outhtmlpath = (outfolder / nssub / f"{name}.html").resolve()
    # and finally prefix it with the nssub if relevant to produce the jinja {{name}}
    name = name if str(nssub == '.') else str(nssub) + "/" + nsname

    # make a backup
    # ensure outfolder exists
    os.makedirs(outbackpath.parent, exist_ok=True)
    shutil.copyfile(nspath, outbackpath)

    # apply jinja2 (building context with baseuri and self)
    prms = dict(name=name, baseuri=baseuri)

    # build jinja2 context - execute
    templates_env = Environment(loader=FileSystemLoader(nsfolder))
    template = templates_env.get_template(str(nspath.relative_to(nsfolder)))
    outcome = template.render(prms)
    log.debug(f"name to use is == {name}")
    log.debug(f"context for templates == {prms}")
    with open(str(outpath), "w") as outfile:
        outfile.write(outcome)

    # apply pylode
    try:
        od = OntDoc(outpath)
        od.make_html(destination=outhtmlpath, include_css=False)
    except PylodeError as ple:
        log.error(f"Failed to process ontology {name} at {nspath} with pylode v.{plv}")
        log.exception(ple)


def publish_ontologies(baseuri, nsfolder, outfolder, logconf=None):
    enable_logging(logconf)

    # default target folder to input folder
    outfolder = nsfolder if outfolder is None else outfolder
    outfolder = Path(outfolder).resolve()
    nsfolder = Path(nsfolder).resolve()
    log.debug(f"publishing ontologies from '{nsfolder}' to '{outfolder}' while applying baseuri={baseuri}")

    # init result set
    ontos = set()

    # todo run over nsfolder and process ontology files
    for folder, dirs, nsfiles in os.walk(nsfolder, topdown=False, followlinks=True):
        for nsname in nsfiles:
            if nsname.endswith('.ttl'):
                log.debug(f"ttl file at {folder} - {nsname} when walking {nsfolder}")
                nssub =  Path(folder).relative_to(nsfolder)
                ontopub(baseuri, nsfolder, nssub, nsname, outfolder)
                ontos.add(f"{str(nssub)}/{nsname}")
    return ontos


def main():
    load_dotenv()

    # read the action inputs
    baseuri = sys.argv[1] if len(sys.argv) > 1 else os.environ.get('BASE_URI')
    nsfolder = sys.argv[2] if len(sys.argv) > 2 else "."
    outfolder = sys.argv[3] if len(sys.argv) > 3 else None
    logconf = sys.argv[4] if len(sys.argv) > 4 else os.environ.get('LOGCONF')

    # do the actual work
    ontos = publish_ontologies(baseuri, nsfolder, outfolder, logconf)

    # set the action outputs
    print(f"::set-output name=ontologies::{ontos}")


if __name__ == "__main__":
    main()
