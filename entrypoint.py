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
import re
from pathlib import Path
from dotenv import load_dotenv
from pathlib import Path
import bs4
from jinja2 import Environment, FileSystemLoader, BaseLoader
from pysubyt import JinjaBasedGenerator, SourceFactory, SinkFactory, GeneratorSettings
from pylode import OntPub, PylodeError, __version__ as plv
from pylode import (
    DCTERMS,
    OWL,
    PROF,
    RDF,
    SKOS,
)
from itertools import chain

log = logging.getLogger("pylode-to-pages")

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


def enable_logging(logconf):
    if logconf is not None and Path(logconf).is_file():
        with open(logconf, "r") as yml_logconf:
            logging.config.dictConfig(yaml.load(yml_logconf, Loader=yaml.SafeLoader))
    else:
        logging.config.dictConfig(
            yaml.load(EMBEDDED_YAML_LOGCONF, Loader=yaml.SafeLoader)
        )
        log.warning(
            f"logconf file '{logconf}' does not exist. Embedded logging config applied as fallback."
        )


def extract_pub_dict(od: OntPub):
    def ont_prop(ont, predicate):
        value = None
        for s in chain(
            ont.subjects(RDF.type, OWL.Ontology),
            ont.subjects(RDF.type, PROF.Profile),
            ont.subjects(RDF.type, SKOS.ConceptScheme),
        ):
            for obj in ont.objects(s, predicate):
                value = str(obj)
        return value

    def od_title():
        return ont_prop(od.ont, DCTERMS.title)

    def od_lastmod():
        return ont_prop(od.ont, DCTERMS.modified)

    return dict(title=od_title(), lastmod=od_lastmod())


def ontopub(baseuri, nsfolder, nssub, nsname, outfolder):
    log.debug(f"ontology to process: {nssub}/{nsname} in {nsfolder}")

    nsfolder = Path(nsfolder)
    outfolder = Path(outfolder)
    nspath = (nsfolder / nssub / nsname).resolve()
    outpath = (outfolder / nssub / str(nsname.replace("_draft", ""))).resolve()
    outbackpath = (
        outfolder / nssub / f"{nsname}.bak"
    ).resolve()  # what does .bak mean? => backup file extension for the original file provided by the user (before it is processed by pylode2pages)
    # extract name for {{ self }} from filename
    name = str(Path(nsname).stem)
    draft = False
    if "_draft" in name:
        draft = True
        name = name.replace("_draft", "")
    # I changed the index.html to name.html since I will be making the index.html in the publish combined index function
    name_html = name + ".html"
    # produce html path and index-path
    outhtmlpath = (outfolder / nssub / f"{name}.html").resolve()
    log.debug(f"> {name} --> outhtmlpath == '{outhtmlpath}'")
    outindexpath = (outfolder / nssub / name).resolve() / name_html
    log.debug(f"> {name} --> outindexpath == '{outindexpath}'")

    # and finally prefix it with the nssub if relevant to produce the jinja {{name}}
    name = name if str(nssub) == "." else str(nssub) + "/" + name
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
    template = templates_env.get_template(
        str(nspath.relative_to(nsfolder)).replace("\\", "/")
    )
    outcome = template.render(prms)
    log.debug(f"> {name} --> context for templates == {prms}")
    with open(str(outpath), "w") as outfile:
        outfile.write(outcome)
    log.debug(f"> {name} --> processed ontlogy written to '{outpath}'")

    nspub = dict(error=True)  # this assumes things will go bad :)
    # check if _draft is in the name
    try:  # apply pylode
        od = OntPub(outpath)
        log.debug(f"> {name} --> ontology loaded to pylode from '{outpath}'")
        # ask pylode to make the html
        od.make_html(destination=outhtmlpath, include_css=False)

        # take the outhtmlpath and open it with bs4
        output_html = open(outhtmlpath, "r")
        soup = bs4.BeautifulSoup(output_html, "html.parser")
        # find all divs with class="property entity"
        # then find the  <th>IRI</th> in that div
        # then take the <td><code>https://example.org/pylode2pages-test/emobonOntology#enaProjAccNum</code></td> that is next to the <th>IRI</th>
        # copy the text between the # and the </code> tag
        # replace the div id with that text

        toc_div = soup.find("div", id="toc")
        for div in soup.find_all("div", class_="property entity"):
            try:
                for th in div.find_all("th"):
                    if th.text == "IRI":
                        iri = th.find_next("td").find("code").text
                        previous_id = div["id"]
                        # find the a href tag in the div with id "toc" and replace the href with the iri.split("#")[1]
                        for a in toc_div.find_all("a"):
                            if a["href"] == "#" + previous_id:
                                a["href"] = "#" + iri.split("#")[1]
                        div["id"] = iri.split("#")[1]
            except:
                pass

        # write the soup back to the file
        with open(outhtmlpath, "w") as output_html:
            output_html.write(str(soup))

        log.debug(f"> {name} --> html produced to '{outhtmlpath}'")
        # also add an extra copy from name.html to name/index.html AND for the css as well
        shutil.copy(outhtmlpath, outindexpath)
        shutil.copy(
            outhtmlpath.parent / "pylode.css", outindexpath.parent / "pylode.css"
        )
        log.debug(f"> {name} --> copy added to '{outindexpath}'")
        # get some minimal metadata from the ttl since pylode loaded that into memory anyway?
        nspub = extract_pub_dict(od)  # if we got here however, things should be ok
        nspub["draft"] = draft
        log.debug(f"> {name} --> ready with result == {nspub}")
        nspub["name"] = name
        nspub["relref"] = str(outindexpath.parent.relative_to(outfolder)).replace(
            "\\", "/"
        )
    except PylodeError as ple:
        log.error(
            f"> {name} --> pylode v.{plv} failed to process ontology at '{nspath}'"
        )
        log.error(f"> {name} --> Error message: {str(ple)}")
        log.exception(ple)
        nspub["error_message"] = f"Pylode error: {str(ple)}"
    except Exception as e:
        log.error(
            f"> {name} --> unexpected failure in processing ontology at '{nspath}'"
        )
        log.error(f"> {name} --> Error message: {str(e)}")
        log.exception(e)
        nspub["error_message"] = f"Unexpected error: {str(e)}"
    finally:
        # return the pub struct with core elements for the overview page
        log.debug(f"> {name} --> returning result == {nspub}")
        return nspub


def publish_misc(baseuri, nsfolder, outfolder):
    otherfiles = ["CNAME"]
    nsfolder = Path(nsfolder)
    outfolder = Path(outfolder)
    for other in otherfiles:
        otherfile = nsfolder / other
        if otherfile.exists():
            shutil.copy(otherfile, outfolder / other)
    # TODO consider generating CNAME file with content derived from baseuri


def publish_combined_index(baseuri, nsfolder, outfolder, template_path, logconf=None):
    enable_logging(logconf)
    # default target folder to input folder
    outfolder = nsfolder if outfolder is None else outfolder
    outfolder = Path(outfolder).resolve()
    nsfolder = Path(nsfolder).resolve()
    log.debug(
        f"publishing combined index from '{nsfolder}' to '{outfolder}' while applying baseuri={baseuri}"
    )

    processing_list = list()

    root_folder_name = outfolder.parts[-1]
    log.debug(f"root folder name is {root_folder_name}")
    # run over nsfolder and process ontology files
    for folder, dirs, nsfiles in os.walk(outfolder, topdown=False, followlinks=True):
        for nsname in nsfiles:
            parent_folder = Path(folder).parts[-1]
            nssub = Path(folder).relative_to(outfolder)
            if parent_folder == root_folder_name:
                continue
            if nsname.endswith(".html"):
                # check if the name contains _vocab
                if nsname.endswith("_vocab.html") or nsname.endswith(
                    "_vocab_draft.html"
                ):
                    prsnt = False
                    for item in processing_list:
                        if item["folder"] == parent_folder:
                            item["vocabularies"] = nsname
                            break
                    if not prsnt:
                        processing_list.append(
                            {
                                "folder": parent_folder,
                                "ontologies": "",
                                "vocabularies": nsname,
                                "nssub": nssub,
                            }
                        )
                    continue
                # go over processing list and check if the parent folder is already present in the folder key of the dict
                prsnt = False
                for item in processing_list:
                    if item["folder"] == parent_folder:
                        item["ontologies"] = nsname
                        prsnt = True
                        break
                if not prsnt:
                    processing_list.append(
                        {
                            "folder": parent_folder,
                            "ontologies": nsname,
                            "vocabularies": "",
                            "nssub": nssub,
                        }
                    )

                # take the last part of the folder
                log.debug(f"parent_folder={parent_folder}")
                log.debug(f"processing {nsname} in {folder} in dir {dirs}")
    # Note: We now keep vocabulary-only entries (when ontologies == "" and vocabularies != "")
    # This allows publishing vocabularies without corresponding ontologies

    # run over the processing list and create the combined index
    # init result sets
    combined = dict()
    combined_in_err = set()
    for item in processing_list:
        nscombined = combined_index_pub(
            baseuri,
            nsfolder,
            item["nssub"],
            item["ontologies"],
            outfolder,
            item["ontologies"],
            item["vocabularies"],
            template_path,
        )
        if nscombined["error"]:
            log.error(f"failed to process combined index for {item['folder']}")
            log.error(f"error message: {nscombined['error_message']}")
            combined_in_err.add(item["folder"])
        combined[item["folder"]] = nscombined
    return combined


def combined_index_pub(
    baseuri, nsfolder, nssub, nsname, outfolder, ontology, vocabulary, template_path
):
    log.debug(f"combined index to process: {nssub}/{nsname} in {nsfolder}")
    log.debug(
        f"other params: baseuri={baseuri}, outfolder={outfolder}/{nssub}, ontology={ontology}, vocabulary={vocabulary}"
    )
    toreturn = dict()
    try:
        # generate a proper index.html file using an embedded jinja-template
        prms = dict(
            ontology=ontology,
            baseuri=baseuri,
            vocabulary=vocabulary,
            nsname=nsname,
            nssub=nssub,
        )
        templates_env = Environment(loader=FileSystemLoader(template_path))
        template = templates_env.get_template("template_combined_index.html")
        outcome = template.render(prms)
        log.debug(f"> INDEX --> context for template == {prms}")
        outindexpath = outfolder / nssub / "index.html"
        with open(str(outindexpath), "w") as outfile:
            outfile.write(outcome)
        log.debug(
            f"> INDEX --> overview of processed combined index written to '{outindexpath}'"
        )
        toreturn["error"] = False
    except Exception as e:
        toreturn["error"] = True
        log.debug(
            f"> INDEX --> error while processing combined index for {nssub}/{nsname}"
        )
        log.error(e)
        toreturn["error_message"] = str(e)
    finally:
        return toreturn


def camel_case(value, auto_convert=True):
    """Convert a value to lower camel case, handling quotes and special characters gracefully.

    Args:
        value: The string value to convert
        auto_convert: If True, converts to camelCase and strips special characters. If False, returns original value.

    Examples:
        "Test One" -> "testOne" (when auto_convert=True)
        "Has \"quotes\" inside" -> "hasQuotesInside" (when auto_convert=True)
        "Multiple,  spaces" -> "multipleSpaces" (when auto_convert=True)
        "Test One" -> "Test One" (when auto_convert=False)
    """
    if not auto_convert:
        return value

    import re
    # Remove quotes and other special characters, keep only alphanumeric and spaces
    cleaned = re.sub(r'[^\w\s]', '', value)
    # Normalize multiple spaces to single space
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    # Split on spaces and convert to camelCase
    words = cleaned.split(" ")
    if not words or not words[0]:
        return value  # Return original if cleaning resulted in empty string
    return words[0].lower() + "".join(word.title() for word in words[1:])


def vocabpub(baseuri, nsfolder, nssub, nsname, outfolder, template_path, auto_camel_case=True):
    log.debug(f"vocab to process: {nssub}/{nsname} in {nsfolder}")
    log.debug(f"other params: baseuri={baseuri}, outfolder={outfolder}, auto_camel_case={auto_camel_case}")
    nspath = (nsfolder / nssub / nsname).resolve()
    outpath = (outfolder / nssub / str(nsname.replace("_draft", ""))).resolve()
    name = str(Path(nsname).stem)
    name_html = name + ".html"
    name = name if str(nssub) == "." else str(nssub) + "/" + name
    outindexpath = (outfolder / nssub / name).resolve() / name_html

    toreturn = dict()
    try:
        if nsname.endswith("_draft.csv"):
            draft = True
        else:
            draft = False

        if draft:
            output_name_html = nsname.replace("_draft.csv", "_vocab.html")
            output_name_ttl = nsname.replace("_draft.csv", "_vocab.ttl")
        else:
            output_name_html = nsname.replace(".csv", "_vocab.html")
            output_name_ttl = nsname.replace(".csv", "_vocab.ttl")
        template_path = template_path
        template_name_html = "template_html.html"
        template_name_ttl = "template_ttl.ttl"
        input_file = nsfolder / nssub / nsname
        log.debug(f"input_file={input_file}")

        # check if the output folder exists, if not create it
        if draft:
            folder_name = nsname.replace("_draft.csv", "")
            signposting = baseuri + "/" + str(nsname).replace("_draft.csv", "") + ".ttl"
        else:
            folder_name = nsname.replace(".csv", "")
            signposting = baseuri + "/" + str(nsname).replace(".csv", "") + ".ttl"
        output_folder = outfolder / nssub / folder_name
        log.debug(f"output_folder={output_folder}")
        if not output_folder.exists():
            output_folder.mkdir(parents=True)
        outindexpath = outfolder / output_name_html
        outttlpath = outfolder / output_name_ttl
        relref = str(outindexpath.relative_to(outfolder)).replace("\\", "/")
        # html generation
        args = {
            "input": input_file.__str__(),
            "output": (output_folder / output_name_html).__str__(),
            "template_path": template_path,
            "template_name": template_name_html,
            "vars_dict": {
                "baseuri": baseuri,
                "signposting": signposting,
                "title": str(nsname + " vocabulary").replace(".csv", ""),
                "relref": str(relref).replace(".html", ""),
                "draft": draft,
            },
        }
        log.debug(f"arguments_pysubytd={args}")
        service = JinjaBasedGenerator(args["template_path"])
        source = {"_": SourceFactory.make_source(args["input"])}
        sink = SinkFactory.make_sink(args["output"], force_output=True)
        settings = GeneratorSettings()
        service.process(args["template_name"], source, settings, sink, args)

        # take the output html and parse it with bs4
        output_html = open(output_folder / output_name_html, "r")
        log.debug(f"output_html={output_html}")
        soup = bs4.BeautifulSoup(output_html, "html.parser")
        # find all divs with class="concept entity"
        # then find the  <th>IRI</th> in that div
        # replace the part after the # with the same part where the same string with not spaces and for each char after the space a capital letter
        # then take the <td><code>https://example.org/pylode2pages-test/emobonOntology#enaProjAccNum</code></td> that is next to the <th>IRI</th>
        # copy the text between the # and the </code> tag
        # replace the div id with that text

        toc_div = soup.find("div", id="toc")
        for div in soup.find_all("div", class_="concept entity"):
            try:
                for th in div.find_all("th"):
                    if th.text == "IRI":
                        iri_element = th.find_next("td").find("code")
                        iri = th.find_next("td").find("code").text
                        log.debug(f"iri={iri}")
                        previous_id = div["id"]
                        # find the a href tag in the div with id "toc" and replace the href with the iri.split("#")[1]
                        for a in toc_div.find_all("a"):
                            if a["href"] == "#" + previous_id:

                                # begin with the changing of the href
                                new_id = camel_case(iri.split("#")[1], auto_camel_case)
                                log.debug(f"new_id={new_id}")
                                a["href"] = "#" + new_id
                        div["id"] = new_id
                        # replace the iri split part with the new_id
                        iri_element.string = iri.replace(iri.split("#")[1], new_id)
            except:
                pass

        # write the soup back to the file
        with open(output_folder / output_name_html, "w") as output_html:
            output_html.write(str(soup))

        # ttl generation
        second_args = {
            "input": input_file.__str__(),
            "output": (outttlpath).__str__(),
            "template_path": template_path,
            "template_name": template_name_ttl,
            "vars_dict": {
                "baseuri": baseuri,
                "signposting": baseuri + "/" + nsname + ".ttl",
                "title": str(nsname + " vocabulary").replace(".csv", ""),
                "relref": str(relref).replace("_vocab.html", ""),
            },
        }
        log.debug(f"arguments_pysubytd={second_args}")
        service = JinjaBasedGenerator(second_args["template_path"])
        source = {"_": SourceFactory.make_source(second_args["input"])}
        sink = SinkFactory.make_sink(second_args["output"], force_output=True)
        service.process(
            second_args["template_name"], source, settings, sink, second_args
        )

        # open the ttl file and convert all IRI fragments to camelCase
        output_ttl = open(outttlpath, "r")
        log.debug(f"output_ttl={output_ttl}")
        ttl_content = output_ttl.read()
        output_ttl.close()

        # Find all unique IRI fragments that need to be converted
        # Pattern matches IRIs like: <baseuri/relref#FRAGMENT>
        base_iri = f"{second_args['vars_dict']['baseuri']}/{second_args['vars_dict']['relref']}#"
        # Match the fragment part after the # (everything until the closing >)
        pattern = re.escape(base_iri) + r'([^>]+)'
        fragments = set(re.findall(pattern, ttl_content))

        # Convert each fragment to camelCase and replace all occurrences
        for fragment in fragments:
            # Strip any trailing whitespace/newlines (but not the fragment content itself)
            fragment_clean = fragment.rstrip()
            new_id = camel_case(fragment_clean, auto_camel_case)
            log.debug(f"Converting IRI fragment: '{fragment_clean}' -> '{new_id}'")
            # Replace all occurrences of this fragment in the content
            old_iri = f"{base_iri}{fragment_clean}"
            new_iri = f"{base_iri}{new_id}"
            ttl_content = ttl_content.replace(old_iri, new_iri)

        # write the changes back to the ttl file
        with open(outttlpath, "w") as output_ttl:
            output_ttl.write(ttl_content)

        shutil.copy((output_folder / output_name_html), outindexpath)
        # shutil.copy((output_folder / output_name_ttl), outttlpath)
        toreturn["error"] = False
        toreturn["draft"] = draft
    except Exception as e:
        toreturn["error"] = True
        toreturn["error_message"] = str(e)
    finally:
        return toreturn


def publish_index_html(
    baseuri, nsfolder, outfolder, template_path, ontos, vocabs, logconf=None
):
    enable_logging(logconf)
    log.debug(msg=f"publishing index.html to {outfolder}")
    log.debug(msg=f"baseuri={baseuri}")
    log.debug(msg=f"ontos={ontos} -- vocabs={vocabs}")

    # make an index.html using a template from the templates folder
    prms = dict(ontos=ontos, baseuri=baseuri, vocabs=vocabs)
    templates_env = Environment(loader=FileSystemLoader(str(template_path)))
    template = templates_env.get_template("template_index.html")
    outcome = template.render(prms)
    log.debug(f"> INDEX --> context for template == {prms}")
    outindexpath = outfolder + "/index.html"
    with open(str(outindexpath), "w") as outfile:
        outfile.write(outcome)


def publish_vocabs(baseuri, nsfolder, outfolder, template_path, logconf=None, ignore_folders=None, auto_camel_case=True):
    enable_logging(logconf)

    # default target folder to input folder
    outfolder = nsfolder if outfolder is None else outfolder
    outfolder = Path(outfolder).resolve()
    nsfolder = Path(nsfolder).resolve()

    # Parse ignore_folders if it's a string
    if isinstance(ignore_folders, str):
        ignore_folders = [f.strip() for f in ignore_folders.split(',') if f.strip()]
    elif ignore_folders is None:
        ignore_folders = []

    log.debug(
        f"publishing vocabs from '{nsfolder}' to '{outfolder}' while applying baseuri={baseuri}"
    )
    if ignore_folders:
        log.info(f"Ignoring folders: {', '.join(ignore_folders)}")
    log.info(f"Auto camelCase conversion: {auto_camel_case}")

    # init result sets
    vocabs = dict()
    vocabs_in_err = set()

    # run over nsfolder and process ontology files
    for folder, dirs, nsfiles in os.walk(nsfolder, topdown=False, followlinks=True):
        # Skip ignored folders
        if should_ignore_path(folder, nsfolder, ignore_folders):
            log.debug(f"Skipping ignored folder: {folder}")
            continue

        for nsname in nsfiles:
            if nsname.endswith(".csv"):
                log.debug(f"csv file at {folder} - {nsname} when walking {nsfolder}")

                nssub = Path(folder).relative_to(nsfolder)
                nskey = f"{str(nssub)}/{nsname}"
                nspub = vocabpub(
                    baseuri, nsfolder, nssub, nsname, outfolder, template_path, auto_camel_case
                )
                if nspub["error"]:
                    log.error(f"Error processing vocabulary {nskey}")
                    if "error_message" in nspub:
                        log.error(f"Error details: {nspub['error_message']}")
                    vocabs_in_err.add(nskey)
                vocabs[nskey] = nspub

    if len(vocabs_in_err) > 0:
        log.warning(f"Failed to process {len(vocabs_in_err)} out of {len(vocabs)} vocabularies")
        for err_vocab in vocabs_in_err:
            log.warning(f"  - {err_vocab}")

    return vocabs


def should_ignore_path(path, nsfolder, ignore_folders):
    """Check if a path should be ignored based on ignore_folders list.

    Args:
        path: The path to check (can be a folder path)
        nsfolder: The base namespace folder
        ignore_folders: List of folder patterns to ignore

    Returns:
        True if the path should be ignored, False otherwise
    """
    if not ignore_folders:
        return False

    # Get the relative path from nsfolder
    try:
        rel_path = Path(path).relative_to(nsfolder)
    except ValueError:
        # If path is not relative to nsfolder, don't ignore
        return False

    # Check each part of the path against ignore patterns
    path_parts = rel_path.parts
    for ignore_pattern in ignore_folders:
        ignore_pattern = ignore_pattern.strip()
        if not ignore_pattern:
            continue
        # Check if any part of the path matches the ignore pattern
        for part in path_parts:
            if part == ignore_pattern or part.startswith(ignore_pattern):
                return True

    return False


def publish_ontologies(baseuri, nsfolder, outfolder, template_path, logconf=None, ignore_folders=None):
    enable_logging(logconf)

    # default target folder to input folder
    outfolder = nsfolder if outfolder is None else outfolder
    outfolder = Path(outfolder).resolve()
    nsfolder = Path(nsfolder).resolve()

    # Parse ignore_folders if it's a string
    if isinstance(ignore_folders, str):
        ignore_folders = [f.strip() for f in ignore_folders.split(',') if f.strip()]
    elif ignore_folders is None:
        ignore_folders = []

    log.debug(
        f"publishing ontologies from '{nsfolder}' to '{outfolder}' while applying baseuri={baseuri}"
    )
    if ignore_folders:
        log.info(f"Ignoring folders: {', '.join(ignore_folders)}")

    # init result sets
    ontos = dict()
    ontos_in_err = set()

    # run over nsfolder and process ontology files
    for folder, dirs, nsfiles in os.walk(nsfolder, topdown=False, followlinks=True):
        # Skip ignored folders
        if should_ignore_path(folder, nsfolder, ignore_folders):
            log.debug(f"Skipping ignored folder: {folder}")
            continue

        for nsname in nsfiles:
            if nsname.endswith(".ttl"):
                log.debug(f"ttl file at {folder} - {nsname} when walking {nsfolder}")
                nssub = Path(folder).relative_to(nsfolder)
                nskey = f"{str(nssub)}/{nsname}"
                nspub = ontopub(baseuri, nsfolder, nssub, nsname, outfolder)
                if bool(
                    nspub.get("error")
                ):  # if the error key is there and set to anything non-False
                    log.error(f"Error processing ontology {nskey}")
                    if "error_message" in nspub:
                        log.error(f"Error details: {nspub['error_message']}")
                    ontos_in_err.add(nskey)
                ontos[nskey] = nspub

    # copy any other stuff outside the actual pylode / ontology stuff
    publish_misc(baseuri, nsfolder, outfolder)

    if len(ontos_in_err) > 0:
        log.error(f"Failed to process {len(ontos_in_err)} out of {len(ontos)} ontologies")
        for err_onto in ontos_in_err:
            log.error(f"  - {err_onto}")
        raise OntoPubException(ontos, ontos_in_err)
    return ontos


def combine_ttls(outfolder):
    """Will combine all the ttl files in the outfolder into a single ttl file

    Args:
        outfolder (str): the folder to combine the ttl files from
    """
    ttl_files = []
    for folder, dirs, nsfiles in os.walk(outfolder, topdown=False, followlinks=True):
        for file in nsfiles:
            if file.endswith(".ttl"):
                # if file does not contain _vocabs then add it to the list
                if not file.endswith("_vocab.ttl"):
                    log.debug(msg=f"found an ontology ttl file {file} in {folder}")
                    ttl_files.append({"folder": folder, "file": file})
    # loop over the ttl_files and check if there is another file with the same name but with _vocabs appedned to it and from the same folder
    for ttl_file in ttl_files:
        vocabs_file = ttl_file["file"].replace(".ttl", "_vocab.ttl")
        vocabs_path = Path(ttl_file["folder"]) / vocabs_file
        if vocabs_path.exists():
            log.debug(msg=f"found vocabs file {vocabs_file} in {ttl_file['folder']}")
            ttl_file["vocabs_file"] = vocabs_file
            ttl_file["vocabs_path"] = vocabs_path
            # read in contents of vocabs file and append them to the ttl file
            with open(vocabs_path, "r") as vocabs_file:
                vocabs_content = vocabs_file.read()
            with open(Path(ttl_file["folder"]) / ttl_file["file"], "a") as ttl_file:
                ttl_file.write(vocabs_content)
            # delete the vocabs file
            os.remove(path=vocabs_path)


class OntoPubException(Exception):
    def __init__(self, ontos: dict, error_ontos: set):
        self.ontos = ontos
        self.error_ontos = error_ontos
        self.message = (
            f"failed to produce all {len(error_ontos)} out of {len(ontos)} found"
        )
        super().__init__(self.message)


def main():
    load_dotenv()
    # read the action inputs
    baseuri = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("BASE_URI")
    nsfolder = sys.argv[2] if len(sys.argv) > 2 else "."
    outfolder = sys.argv[3] if len(sys.argv) > 3 else None
    logconf = sys.argv[4] if len(sys.argv) > 4 else os.environ.get("LOGCONF")
    ignore_folders = sys.argv[5] if len(sys.argv) > 5 else os.environ.get("IGNORE_FOLDERS", "")
    auto_camel_case_str = sys.argv[6] if len(sys.argv) > 6 else os.environ.get("AUTO_CAMEL_CASE", "true")
    # Convert string to boolean
    auto_camel_case = auto_camel_case_str.lower() in ("true", "1", "yes", "on")
    # load in logconf
    enable_logging(logconf)
    myfolder = Path(__file__).parent.absolute()
    template_path = myfolder / "templates"
    log.debug(f"template_path={template_path} -- exists? {template_path.exists()}")

    if ignore_folders:
        log.info(f"Configured to ignore folders: {ignore_folders}")
    log.info(f"Auto camelCase conversion enabled: {auto_camel_case}")

    # do the actual work
    # TODO consider some way to deal with the possible OntoPubException
    try:
        ontos = publish_ontologies(baseuri, nsfolder, outfolder, template_path, logconf, ignore_folders)
    except OntoPubException as ope:
        log.error("=" * 80)
        log.error("ONTOLOGY PROCESSING FAILED")
        log.error("=" * 80)
        log.error(ope.message)
        log.error("Failed ontologies:")
        for err_onto in ope.error_ontos:
            log.error(f"  - {err_onto}")
        log.error("=" * 80)
        raise

    vocabs = publish_vocabs(baseuri, nsfolder, outfolder, template_path, logconf, ignore_folders, auto_camel_case)
    log.debug(msg=f"ontos={ontos.keys()} -- vocabs={vocabs.keys()}")

    # function here that will make the index.html file with info concerning the ontologies and the vocabularies
    publish_index_html(
        baseuri, nsfolder, outfolder, template_path, ontos, vocabs, logconf
    )
    combine_ttls(outfolder)

    # crawl the outfolder and for each ttl file that does not contain _vocab or is the index file.
    # create a line in the <head> of the index.html file that links to the ttl file
    # line example <link
    #  href="https://example.com/ontologies/ontology.ttl"
    #  rel="describedby"
    #  type="text/turtle"
    # />

    for folder, dirs, nsfiles in os.walk(outfolder, topdown=False, followlinks=True):
        for file in nsfiles:
            if (
                file.endswith(".html")
                and not file.endswith("index.html")
                and not file.endswith("_vocab.html")
            ):
                file_path = Path(folder) / file
                with open(file_path, "r") as html_file:
                    html_content = html_file.read()
                    # add <link
                    #  href="./{{file}}.ttl"
                    #  rel="describedby"
                    #  type="text/turtle"
                    # />
                    # to the head of the html file
                    html_content = html_content.replace(
                        "</head>",
                        f'<link href="./{file.replace(".html", "")}.ttl" rel="describedby" type="text/turtle" /></head>',
                    )
                with open(file_path, "w") as html_file:
                    html_file.write(html_content)

    # function here that will genreate an index.html file with iframes for the ontology and for the possible vocabularies
    # the following function is deprecated
    # publish_combined_index(baseuri, nsfolder, outfolder, template_path, logconf)

    # set the action outputs
    print(f"::set-output name=ontologies::{ontos.keys()}")
    print(f"::set-output name=vocabs::{vocabs.keys()}")


if __name__ == "__main__":
    main()
