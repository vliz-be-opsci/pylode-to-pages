#!/usr/bin/env -S python3 -B

# NOTE: If you are using an alpine docker image
# such as pyaction-lite, the -S option above won't
# work. The above line works fine on other linux distributions
# such as debian, etc, so the above line will work fine
# if you use pyaction:4.0.0 or higher as your base docker image.

import sys
import os
import logging
import logging.config
import yaml
from dotenv import load_dotenv


log = logging.getLogger('pylode2pages')


def enable_logging(logconf):
    if logconf is not None:
        with open(logconf, 'r') as yml_logconf:
            logging.config.dictConfig(yaml.load(yml_logconf, Loader=yaml.SafeLoader))


def ontopub(outfolder, nsfolder, nsname, baseurl, copy_sources = True):
    nspath = os.path.join(nsfolder, nsname)
    log.debug(f"ontology to process: {nsname} in {nsfolder}")
    # extract name for {{ self }} from filename
    # copy source
    # make a backup
    # make real namespace_url
    # apply jinja2 (building context with baseurl and self)
    # apply pylode


def publish_ontologies(outfolder, nsfolder, baseurl, logconf = None):
    enable_logging(logconf)

    # default target folder to input folder
    outfolder = nsfolder if outfolder is None else outfolder
    copy_sources = bool(outfolder != nsfolder) # only if we build into another folder then make copies!
    log.debug(f"publishing ontologies from '{nsfolder}' to '{outfolder}' while applying baseurl={baseurl}")

    # ensure outfolder exists
    os.makedirs(outfolder, exist_ok=True)

    # todo if no baseurl, then no jinja processing
    log.debug(f"baseurl set to [{baseurl}]")

    # todo jinja processing

    # init result list
    ontos = list()

    # todo run over nsfolder and process ontology files
    for root, dirs, nsfiles in os.walk(nsfolder, topdown=False, followlinks=True):
        for nsname in nsfiles:
            if nsname.endswith('.ttl'):
                ontopub(outfolder, root, nsname, baseurl, copy_sources)
                ontos.append(nsname)
    return ontos


def main():
    load_dotenv()

    # read the action inputs
    nsfolder = sys.argv[1] if len(sys.argv) > 1 else "."
    baseurl = sys.argv[2] if len(sys.argv) > 2 else os.environ.get('BASE_URL')
    logconf = sys.argv[3] if len(sys.argv) > 3 else os.environ.get('LOGCONF')

    # do the actual work
    ontos = publish_ontologies(None, nsfolder, baseurl, logconf)

    # set the action outputs
    print(f"::set-output name=ontologies::{ontos}")


if __name__ == "__main__" :
    main()
