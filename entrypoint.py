#!/usr/bin/env -S python3 -B

# NOTE: If you are using an alpine docker image
# such as pyaction-lite, the -S option above won't
# work. The above line works fine on other linux distributions
# such as debian, etc, so the above line will work fine
# if you use pyaction:4.0.0 or higher as your base docker image.

from importlib.abc import Loader
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


log = logging.getLogger('pylode-to-pages')


EMBEDDED_YAML_LOGCONF = """
version: 1
formatters:
  base:
    format: '%(asctime)-18s @%(name)-20s [%(levelname)-8s] %(message)s'
    datefmt: '%Y-%m-%d %H:%M:%S'
handlers:
  stderr:
    class: logging.StreamHandler
    level: DEBUG
    formatter: base
    stream: ext://sys.stderr
loggers:
  pylode-to-pages:
    level: DEBUG
root:
  level: DEBUG
  handlers: [stderr]
"""


EMBEDDED_INDEX_TEMPLATE=""""
{%for onto in ontos%}
  {{onto.name}} - {{onto.title}} - {{onto.lastmod}}
{%endfor %}
"""


def enable_logging(logconf):
    if logconf is not None and Path(logconf).is_file():
        with open(logconf, 'r') as yml_logconf:
            logging.config.dictConfig(yaml.load(yml_logconf, Loader=yaml.SafeLoader))
    else:
        logging.config.dictConfig(yaml.load(EMBEDDED_YAML_LOGCONF, Loader=yaml.SafeLoader))
        log.warning(f"logconf file '{logconf}' does not exist. Embedded logging config applied as fallback.")


def extract_pub_dict(od: OntDoc):
    # TODO- inspect the embedded ont graph in search for title and lastmod -- like pylode is doing it!
    return dict(title="todo extracted title", lastmod="todo last mod")


def ontopub(baseuri, nsfolder, nssub, nsname, outfolder):
    log.debug(f"ontology to process: {nssub}/{nsname} in {nsfolder}")

    nsfolder = Path(nsfolder)
    outfolder = Path(outfolder)
    nspath = (nsfolder / nssub / nsname).resolve()
    outpath = (outfolder / nssub / nsname).resolve()
    outbackpath = (outfolder / nssub / f"{nsname}.bak").resolve()

    # extract name for {{ self }} from filename
    name = str(Path(nsname).stem)
    # produce html path ans index-symlink
    outhtmlpath = (outfolder / nssub / f"{name}.html").resolve()
    log.debug(f"> {name} --> outhtmlpath == '{outhtmlpath}'")
    outindexpath = (outfolder / nssub / name).resolve() / "index.html"
    log.debug(f"> {name} --> outindexpath == '{outindexpath}'")

    # and finally prefix it with the nssub if relevant to produce the jinja {{name}}
    name = name if str(nssub) == '.' else str(nssub) + "/" + name
    log.debug(f"> {name} --> ontopub work started")

    # ensure outfolder exists (indexpath is the deepest one) 
    os.makedirs(outindexpath.parent, exist_ok=True)
    log.debug(f"> {name} --> created folders to contain '{outindexpath}'")
    # make a backup
    shutil.copyfile(nspath, outbackpath)
    log.debug(f"> {name} --> backup original provided at '{outbackpath}'")

    # apply jinja2 (building context with baseuri and self) -- build jinja2 context - execute
    prms = dict(name=name, baseuri=baseuri)
    templates_env = Environment(loader=FileSystemLoader(nsfolder))
    template = templates_env.get_template(str(nspath.relative_to(nsfolder)))
    outcome = template.render(prms)
    log.debug(f"> {name} --> context for templates == {prms}")
    with open(str(outpath), "w") as outfile:
        outfile.write(outcome)
    log.debug(f"> {name} --> processed ontlogy written to '{outpath}'")

    nspub = dict(error=True) # this assumes things will go bad :)
    # apply pylode
    try:
        od = OntDoc(outpath)
        log.debug(f"> {name} --> ontology loaded to pylode from '{outpath}'")
        # ask pylode to make the html
        od.make_html(destination=outhtmlpath, include_css=False)
        log.debug(f"> {name} --> html produced to '{outhtmlpath}'")
        # also add a symlink from name.html to name/index.html
        if (outindexpath.is_file()): # in case this would already exist
            os.remove(outindexpath)
        os.symlink(outhtmlpath, outindexpath)
        log.debug(f"> {name} --> symlink added to '{outindexpath}'")
        # get some minimal metadata from the ttl since pylode loaded that into memory anyway?
        nspub = extract_pub_dict(od)  # if we got here however, things should be ok
        log.debug(f"> {name} --> ready with result == {nspub}")
    except PylodeError as ple:
        log.error(f"> {name} --> pylode v.{plv} failed to process ontology at '{nspath}'")
        log.exception(ple)
    except Exception as e:
        log.error(f"> {name} -->  unexpected failure in processing ontology at '{nspath}'")
        log.exception(e)
    finally:    
        # return the pub struct with core elements for the overview page
        log.debug(f"> {name} --> returning result == {nspub}")
        return nspub


def publish_ontologies(baseuri, nsfolder, outfolder, logconf=None):
    enable_logging(logconf)

    # default target folder to input folder
    outfolder = nsfolder if outfolder is None else outfolder
    outfolder = Path(outfolder).resolve()
    nsfolder = Path(nsfolder).resolve()
    log.debug(f"publishing ontologies from '{nsfolder}' to '{outfolder}' while applying baseuri={baseuri}")

    # init result sets
    ontos = dict()
    ontos_in_err = set()

    # run over nsfolder and process ontology files
    for folder, dirs, nsfiles in os.walk(nsfolder, topdown=False, followlinks=True):
        for nsname in nsfiles:
            if nsname.endswith('.ttl'):
                log.debug(f"ttl file at {folder} - {nsname} when walking {nsfolder}")
                nssub =  Path(folder).relative_to(nsfolder)
                nskey=f"{str(nssub)}/{nsname}"
                nspub=ontopub(baseuri, nsfolder, nssub, nsname, outfolder)
                if bool(nspub.get("error")):  # if the error key is there and set to anything non-False 
                    log.debug(f"error processing {nskey} --> {nspub}")
                    ontos_in_err.add(nskey)
                ontos[nskey]=nspub

    # generate a proper index.html file using an embedded jinja-template

    if len(ontos_in_err) > 0:
        raise OntoPubException(ontos, ontos_in_err)
    # else
    return ontos


class OntoPubException(Exception):
    def __init__(self, ontos: dict, error_ontos: set):
        self.ontos = ontos
        self.error_ontos = error_ontos
        self.message = f"failed to produce all {len(error_ontos)} out of {len(ontos)} found"
        super().__init__(self.message)


def main():
    load_dotenv()

    # read the action inputs
    baseuri = sys.argv[1] if len(sys.argv) > 1 else os.environ.get('BASE_URI')
    nsfolder = sys.argv[2] if len(sys.argv) > 2 else "."
    outfolder = sys.argv[3] if len(sys.argv) > 3 else None
    logconf = sys.argv[4] if len(sys.argv) > 4 else os.environ.get('LOGCONF')

    # do the actual work
    # TODO consider some way to deal with the possible OntoPubException
    ontos = publish_ontologies(baseuri, nsfolder, outfolder, logconf)

    # set the action outputs
    print(f"::set-output name=ontologies::{ontos.keys()}")


if __name__ == "__main__":
    main()
