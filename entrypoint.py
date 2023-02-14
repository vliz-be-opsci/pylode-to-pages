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
from jinja2 import Environment, FileSystemLoader, BaseLoader
from pysubyt import JinjaBasedGenerator, SourceFactory, SinkFactory, Settings
from pylode import OntDoc, PylodeError, __version__ as plv
from pylode import (
    DCTERMS,
    OWL,
    PROF,
    RDF,
    SKOS,
)
from itertools import chain


log = logging.getLogger('pylode-to-pages')

EMBEDDED_INDEX_IFRAME_TEMPLATE = """
<html>
<head>
  <title>Overview of {{baseuri}} namespace</title>
  <style>
        #pylode {
            position: fixed;
            top: 170px;
            left: -150px;
            font-size: small;
            transform: rotate(-90deg);
            color: grey;
        }
        html {
            scroll-behavior: smooth;
        }
        #pylode a {
            font-size: 2em;
            font-weight: bold;
            text-decoration: none;
            color: #005A9C;
        }
        #pylode a:hover {
            color: #333;
        }
        #pylode #p {
            color: #329545;
        }
        #pylode #y {
            color: #f9cb33;
        }
        #pylode #version {
            font-size: 1.0em;
        }

        .cardinality {
            font-style: italic;
            color: #aa00aa;
        }

        dl {
            /*border: 1px solid navy;*/
            /*padding:5px;*/
        }

        dt {
            font-weight: bold;
            padding: 0;
        }

        dd {
            margin-bottom: 10px;
            padding-top: 7px;
        }

        #metadata ul,
        #classes ul {
            list-style-type: none;
        }

        #metadata ul li,
        #classes ul li {
            margin-left: -40px;
        }

        ul.hlist {
            list-style-type: none;
            border: 1px solid navy;
            padding:5px;
            background-color: #F4FFFF;
        }

        ul.hierarchy {
            border: 1px solid navy;
            padding: 5px 25px 5px 25px;
            background-color: #F4FFFF;
        }


        ul.hlist li {
            display: inline;
            margin-right: 10px;
        }

        .entity {
            border: 1px solid navy;
            margin:5px 0 5px 0;
            padding: 5px;
        }

        .entity th {
            width: 150px;
            vertical-align: top;
        }

        .entity th,
        .entity td {
            padding-bottom: 20px;
        }

        .entity table th {
            text-align: left;
        }

        section#overview img {
            max-width: 1000px;
        }

        h1, h2, h3, h4, h5, h6 {
            text-align: left
        }
        h1, h2, h3 {
            color: #005A9C; background: white
        }
        h1 {
            font: 170% sans-serif;
            line-height: 110%;
        }
        h2 {
            font: 140% sans-serif;
            margin-top:40px;
        }
        h3 {
            font: 120% sans-serif;
            margin-top: 20px;
            padding-bottom: 5px;
            border-bottom: 1px solid navy;
        }
        h4 { font: bold 100% sans-serif }
        h5 { font: italic 100% sans-serif }
        h6 { font: small-caps 100% sans-serif }

        body {
            padding: 2em 70px 2em 70px;
            margin: 0;
            font-family: sans-serif;
            color: black;
            background: white;
            background-position: top left;
            background-attachment: fixed;
            background-repeat: no-repeat;
            text-align: left;
        }

        section {
            max-width: 1500px;
        }

        .figure {
            margin-bottom: 20px;
        }

        :link { color: #00C; background: transparent }
        :visited { color: #609; background: transparent }
        a:active { color: #C00; background: transparent }

        .sup-c,
        .sup-op,
        .sup-fp,
        .sup-dp,
        .sup-ap,
        .sup-p,
        .sup-ni,
        .sup-con,
        .sup-col {
            cursor:help;
        }

        .sup-c {
            color:orange;
        }

        .sup-op {
            color:navy;
        }

        .sup-fp {
            color:lightskyblue;
        }

        .sup-dp {
            color:green;
        }

        .sup-ap {
            color:darkred;
        }

        .sup-p {
            color:black;
        }

        .sup-ni {
            color:brown;
        }

        .sup-con {
            color:orange;
        }

        .sup-col {
            color:darkred;
        }

        sup {
            margin-left: -3px;
        }
        code {
            font-size: large;
            color: darkred;
        }

        /* less prominent links for properties */
        .proplink {
            color: #336;
            text-decoration: none;
        }

#toc {
    position: fixed;
    top: 0;
    right: 0;
    z-index: 2;
    height: 100%;
    overflow-y: auto;
    padding: 10px;
    border: solid 1px navy;
    font-size: small;
    width: 180px;
}
#toc h3 {
    margin-top: 5px;
}

#toc ul {
    list-style: none;
    padding-left: 0;
}

#toc .first > li {
    margin-top: 5px;
}

#toc .second,
#toc .third {
    padding-left: 10px;
}

#content {
    width: calc(100% - 150px);
}

.hover_property {
    text-decoration: none;
    border-bottom: dashed 1px;
}

.setclass {
    list-style-type: none;
}

code{
    word-wrap: break-word;
  }
  table {
    table-layout: fixed;
    width: 100%;
  }
  td {
    word-wrap: break-word;
  }
	</style>
    <link href="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAABhklEQVQ4jbWPzStEURjG3yQLirlGKUnKFO45Z+SjmXvnnmthQcpCoVhYmD/AwmJiI3OvZuZc2U3UlKU0/gAslMw9JgvhHxAr2fko7r0jHSsl+TgbTz2Lt5731/MASEiJW9ONml2QyX6rsGalmnT74v8BDf12hxJfpV8d1uwNKUBYszabdFv84L8B9X0rESVmmUup2fme0cVhJWaZHw4NWL1SewEAfDe6H3Dy6Ll456WEJsRZS630MwCAOI20ei5OBpxse5zcBZw8eS4uPpfIuDiCainIg9umBCU0GZzgLZ9Hn31OgoATL+CkLDGB5H1OKj4nFd/FBxUXJ0UZNb4edw/6nLyJXaj5FeCVyPLNIVmYK8TG1IwWb16L1gEACAFV90ftoT8bdOX0EeyY99gxBXZMgRz6qGb1KantAACI0UvE6F5XJqEjpsdURouI0Vt5gGOUkUNnPu7ObGIIMfNaGqDmjDRi9FZldF1lRgYzeqUyeoiY4ag5Iy3RgOYRM8+/M2bG8efsO4hGrpmJseyMAAAAAElFTkSuQmCC" rel="icon" sizes="16x16" type="image/png">
    <link href="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAC40lEQVRYhe2UT0hUQRzHp6Iss1B3VZKIDbbdfW9mnoi4f3zzjkJQeOgS0SEIb1EWBGGlLLu460zQPQM1unUIIjA6rfpm6ZAhHjoIRVQUFUlEbG+euTsdXG1d3VL3bVD4g+9h+L35fT/8fvN7ADgY9aHY5fpIvK82HO9ysu66wxWOzbkjcekKx0a2ALYA/n2AGi3a6ArFezcidziecQygNhhrcUficjP6PwBqtGijKxy/thnVBePHywYoDsFhl53GV8SEcsTx4usCMLUewTVpc23BNvEzm6Neyf1+KcG2vwqwUjgrOJq2JmHftwmkVBRGTvncFodnbI7vChO/FRznCmHsNM7aHM9Yk7Df5iqsLMw9sMNOK2g+jS4IEz0UJv4iuJZb2RltWnB4UZqH6ioGAgAAGe5vtiZhtzDx7OoRadLmeM7m6IRjhnLMW2Vx1bA5GhAmnhIcz6/xNj4Ujsky8UspwfayjDPjsF2Y6L7N8Vzx/BfP+KPg6LbgSqd8DnfJW2CnbaLhfH5ephpqygJYvQU4Z3P82TLRsDDhUTnmrSq+Y3N0Mg+Xldy/zwEAnLMWZ3pHpNExmfLs/t0dOdVcbT0JeKxUwFP2VljjqiE47Jp53LTXNxhsUZjerTByXWX6VZWRs/4bIQ2ACv+UAomgDzLCISNZxAxZKMhIDjLy1JfsaK+I+eGBUBNk5E2x8RogX/PdcDZUqieWTSh5D6nOVKqfhoycUmlHFFIyu5RXqf7AcQDISCpv/tqbMBqK883RtmpISRoxQyJKPgGn3wNk5NEigDFa6hslqV/Kj+FdBQD0bshIDlKSLlVcoWQo36UhR80BAMB73lulMn0EMpJTqD6qJiOt3mho/8GbkT2BZNgDB/V+RI0fkOrT3kRIVQbaDizJm2hdNbINBxwk5xAj3yEjuV9rZ1iIkgxixkLBA83mz8uCjLwoGwAx0vOnFSy5mtR4VTaAQvVORMnwZgSpzkrV/QmdE2tKe46+MQAAAABJRU5ErkJggg==" rel="icon" sizes="32x32" type="image/png">
    <meta content="text/html; charset=utf-8" http-equiv="Content-Type">
</head>
<body class="container">
<div id="content">
    <div class="section" id="ontologies_and_vocabs">
        <h2>Ontologies and vocabularies</h2>
        {%if ontology%}
            <div class="concept entity" id="{{ontology}}">
                <h3 class="title">
                    <a href="{{ontology}}">{{ontology}}/</a>
                    <sup class="sup-op" title="ontology">Ontology</sup>
                </h3>
                <table>
                    <tr>
                        <th>IRI</th>
                        <td>
                            <code>{{baseuri}}/{{nssub}}/{{ontology}}</code>
                        </td>
                    </tr>
                </table>  
            </div>
        {%endif%}
        {%if vocabulary%}
            <div class="concept entity" id="{{vocabulary}}">
                <h3 class="title">
                    <a href="{{vocabulary}}">{{vocabulary}}/</a>
                    <sup class="sup-op" title="vocabulary">Vocabulary</sup>
                </h3>
                <table>
                    <tr>
                        <th>IRI</th>
                        <td>
                            <code>{{baseuri}}/{{nssub}}/{{vocabulary}}</code>
                        </td>
                    </tr>
                </table>  
            </div>
        {%endif%}
    </div>
</div>
<div id="pylode">
  <p>made by 
    <a href="https://github.com/vliz-be-opsci/pylode-to-pages">
      <span id="p">Pylode</span>
      <span id="y">-To-Pages</span>
      <span>@VLIZ</span>
    </a>
  </p>
</div>
</body>
</html>
"""


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


EMBEDDED_INDEX_TEMPLATE = """
<html>
<head>
  <title>Overview of {{baseuri}} namespace</title>
  <style>
        #pylode {
            position: fixed;
            top: 170px;
            left: -150px;
            font-size: small;
            transform: rotate(-90deg);
            color: grey;
        }
        html {
            scroll-behavior: smooth;
        }
        #pylode a {
            font-size: 2em;
            font-weight: bold;
            text-decoration: none;
            color: #005A9C;
        }
        #pylode a:hover {
            color: #333;
        }
        #pylode #p {
            color: #329545;
        }
        #pylode #y {
            color: #f9cb33;
        }
        #pylode #version {
            font-size: 1.0em;
        }

        .cardinality {
            font-style: italic;
            color: #aa00aa;
        }

        dl {
            /*border: 1px solid navy;*/
            /*padding:5px;*/
        }

        dt {
            font-weight: bold;
            padding: 0;
        }

        dd {
            margin-bottom: 10px;
            padding-top: 7px;
        }

        #metadata ul,
        #classes ul {
            list-style-type: none;
        }

        #metadata ul li,
        #classes ul li {
            margin-left: -40px;
        }

        ul.hlist {
            list-style-type: none;
            border: 1px solid navy;
            padding:5px;
            background-color: #F4FFFF;
        }

        ul.hierarchy {
            border: 1px solid navy;
            padding: 5px 25px 5px 25px;
            background-color: #F4FFFF;
        }


        ul.hlist li {
            display: inline;
            margin-right: 10px;
        }

        .entity {
            border: 1px solid navy;
            margin:5px 0 5px 0;
            padding: 5px;
        }

        .entity th {
            width: 150px;
            vertical-align: top;
        }

        .entity th,
        .entity td {
            padding-bottom: 20px;
        }

        .entity table th {
            text-align: left;
        }

        section#overview img {
            max-width: 1000px;
        }

        h1, h2, h3, h4, h5, h6 {
            text-align: left
        }
        h1, h2, h3 {
            color: #005A9C; background: white
        }
        h1 {
            font: 170% sans-serif;
            line-height: 110%;
        }
        h2 {
            font: 140% sans-serif;
            margin-top:40px;
        }
        h3 {
            font: 120% sans-serif;
            margin-top: 20px;
            padding-bottom: 5px;
            border-bottom: 1px solid navy;
        }
        h4 { font: bold 100% sans-serif }
        h5 { font: italic 100% sans-serif }
        h6 { font: small-caps 100% sans-serif }

        body {
            padding: 2em 70px 2em 70px;
            margin: 0;
            font-family: sans-serif;
            color: black;
            background: white;
            background-position: top left;
            background-attachment: fixed;
            background-repeat: no-repeat;
            text-align: left;
        }

        section {
            max-width: 1500px;
        }

        .figure {
            margin-bottom: 20px;
        }

        :link { color: #00C; background: transparent }
        :visited { color: #609; background: transparent }
        a:active { color: #C00; background: transparent }

        .sup-c,
        .sup-op,
        .sup-fp,
        .sup-dp,
        .sup-ap,
        .sup-p,
        .sup-ni,
        .sup-con,
        .sup-col {
            cursor:help;
        }

        .sup-c {
            color:orange;
        }

        .sup-op {
            color:navy;
        }

        .sup-fp {
            color:lightskyblue;
        }

        .sup-dp {
            color:green;
        }

        .sup-ap {
            color:darkred;
        }

        .sup-p {
            color:black;
        }

        .sup-ni {
            color:brown;
        }

        .sup-con {
            color:orange;
        }

        .sup-col {
            color:darkred;
        }

        sup {
            margin-left: -3px;
        }
        code {
            font-size: large;
            color: darkred;
        }

        /* less prominent links for properties */
        .proplink {
            color: #336;
            text-decoration: none;
        }

#toc {
    position: fixed;
    top: 0;
    right: 0;
    z-index: 2;
    height: 100%;
    overflow-y: auto;
    padding: 10px;
    border: solid 1px navy;
    font-size: small;
    width: 180px;
}
#toc h3 {
    margin-top: 5px;
}

#toc ul {
    list-style: none;
    padding-left: 0;
}

#toc .first > li {
    margin-top: 5px;
}

#toc .second,
#toc .third {
    padding-left: 10px;
}

#content {
    width: calc(100% - 150px);
}

.hover_property {
    text-decoration: none;
    border-bottom: dashed 1px;
}

.setclass {
    list-style-type: none;
}

code{
    word-wrap: break-word;
  }
  table {
    table-layout: fixed;
    width: 100%;
  }
  td {
    word-wrap: break-word;
  }
	</style>
    <link href="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAABhklEQVQ4jbWPzStEURjG3yQLirlGKUnKFO45Z+SjmXvnnmthQcpCoVhYmD/AwmJiI3OvZuZc2U3UlKU0/gAslMw9JgvhHxAr2fko7r0jHSsl+TgbTz2Lt5731/MASEiJW9ONml2QyX6rsGalmnT74v8BDf12hxJfpV8d1uwNKUBYszabdFv84L8B9X0rESVmmUup2fme0cVhJWaZHw4NWL1SewEAfDe6H3Dy6Ll456WEJsRZS630MwCAOI20ei5OBpxse5zcBZw8eS4uPpfIuDiCainIg9umBCU0GZzgLZ9Hn31OgoATL+CkLDGB5H1OKj4nFd/FBxUXJ0UZNb4edw/6nLyJXaj5FeCVyPLNIVmYK8TG1IwWb16L1gEACAFV90ftoT8bdOX0EeyY99gxBXZMgRz6qGb1KantAACI0UvE6F5XJqEjpsdURouI0Vt5gGOUkUNnPu7ObGIIMfNaGqDmjDRi9FZldF1lRgYzeqUyeoiY4ag5Iy3RgOYRM8+/M2bG8efsO4hGrpmJseyMAAAAAElFTkSuQmCC" rel="icon" sizes="16x16" type="image/png">
    <link href="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAC40lEQVRYhe2UT0hUQRzHp6Iss1B3VZKIDbbdfW9mnoi4f3zzjkJQeOgS0SEIb1EWBGGlLLu460zQPQM1unUIIjA6rfpm6ZAhHjoIRVQUFUlEbG+euTsdXG1d3VL3bVD4g+9h+L35fT/8fvN7ADgY9aHY5fpIvK82HO9ysu66wxWOzbkjcekKx0a2ALYA/n2AGi3a6ArFezcidziecQygNhhrcUficjP6PwBqtGijKxy/thnVBePHywYoDsFhl53GV8SEcsTx4usCMLUewTVpc23BNvEzm6Neyf1+KcG2vwqwUjgrOJq2JmHftwmkVBRGTvncFodnbI7vChO/FRznCmHsNM7aHM9Yk7Df5iqsLMw9sMNOK2g+jS4IEz0UJv4iuJZb2RltWnB4UZqH6ioGAgAAGe5vtiZhtzDx7OoRadLmeM7m6IRjhnLMW2Vx1bA5GhAmnhIcz6/xNj4Ujsky8UspwfayjDPjsF2Y6L7N8Vzx/BfP+KPg6LbgSqd8DnfJW2CnbaLhfH5ephpqygJYvQU4Z3P82TLRsDDhUTnmrSq+Y3N0Mg+Xldy/zwEAnLMWZ3pHpNExmfLs/t0dOdVcbT0JeKxUwFP2VljjqiE47Jp53LTXNxhsUZjerTByXWX6VZWRs/4bIQ2ACv+UAomgDzLCISNZxAxZKMhIDjLy1JfsaK+I+eGBUBNk5E2x8RogX/PdcDZUqieWTSh5D6nOVKqfhoycUmlHFFIyu5RXqf7AcQDISCpv/tqbMBqK883RtmpISRoxQyJKPgGn3wNk5NEigDFa6hslqV/Kj+FdBQD0bshIDlKSLlVcoWQo36UhR80BAMB73lulMn0EMpJTqD6qJiOt3mho/8GbkT2BZNgDB/V+RI0fkOrT3kRIVQbaDizJm2hdNbINBxwk5xAj3yEjuV9rZ1iIkgxixkLBA83mz8uCjLwoGwAx0vOnFSy5mtR4VTaAQvVORMnwZgSpzkrV/QmdE2tKe46+MQAAAABJRU5ErkJggg==" rel="icon" sizes="32x32" type="image/png">
    <meta content="text/html; charset=utf-8" http-equiv="Content-Type">
</head>
<body class="container">
<div id="content">
    <div class="section" id="metadata">
        <h1>Overview of described vocabularies in <a href="{{baseuri}}">this namespace</a>.</h1>
    </div>
    <div class="section" id="ontologies_and_vocabs">
        <h2>Ontologies and vocabularies</h2>
        {%for key,onto in ontos.items()%}
            <div class="concept entity" id="{{onto.title}}">
                <h3 class="title">
                    <a href="{{onto.relref}}/index">{{onto.name}}/</a>
                    <sup class="sup-op" title="ontology">O</sup>
                </h3>
                <table>
                    <tr>
                        <th>IRI</th>
                        <td>
                            <code>{{baseuri}}/{{onto.relref}}</code>
                        </td>
                    </tr>
                    <tr>
                        <th>
                            <span class="hover_property">Title</span>
                        </th>
                        <td>
                            <p>{{onto.title}}</p>
                        </td>
                    </tr>
                    <tr>
                        <th>
                            <span class="hover_property">Last modified</span>
                        </th>
                        <td>
                            <p>{{onto.lastmod}}</p>
                        </td>
                    </tr>
                </table>  
            </div>
        {%endfor %}
    </div>
</div>
<div id="pylode">
  <p>made by 
    <a href="https://github.com/vliz-be-opsci/pylode-to-pages">
      <span id="p">Pylode</span>
      <span id="y">-To-Pages</span>
      <span>@VLIZ</span>
    </a>
  </p>
</div>
<div id="toc">
  <h3>Table of Contents</h3>
  <ul class="first">
    <li>
      <h4>
        <a href="#metadata">Metadata</a>
      </h4>
    </li>
    <li>
      <h4>
        <a href="#ontologies_and_vocabs">Ontologies and vocabularies</a>
      </h4>
      <ul class="second">
        {%for key,onto in ontos.items()%}
        <li>
          <a href="#{{onto.title}}">{{onto.name}}</a>
        <li>
        {% endfor %}
      </ul>
    </li>
  </ul>
</div>
</body>
</html>
"""


def enable_logging(logconf):
    if logconf is not None and Path(logconf).is_file():
        with open(logconf, 'r') as yml_logconf:
            logging.config.dictConfig(yaml.load(yml_logconf, Loader=yaml.SafeLoader))
    else:
        logging.config.dictConfig(yaml.load(EMBEDDED_YAML_LOGCONF, Loader=yaml.SafeLoader))
        log.warning(f"logconf file '{logconf}' does not exist. Embedded logging config applied as fallback.")


def extract_pub_dict(od: OntDoc):
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
    outpath = (outfolder / nssub / nsname).resolve()
    outbackpath = (outfolder / nssub / f"{nsname}.bak").resolve()

    # extract name for {{ self }} from filename
    name = str(Path(nsname).stem)
    # I changed the index.html to name.html since I will be making the index.html in the publish combined index function
    name_html = name + ".html"
    # produce html path and index-path
    outhtmlpath = (outfolder / nssub / f"{name}.html").resolve()
    log.debug(f"> {name} --> outhtmlpath == '{outhtmlpath}'")
    outindexpath = (outfolder / nssub / name).resolve() / name_html
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
    template = templates_env.get_template(str(nspath.relative_to(nsfolder)).replace("\\", "/"))
    outcome = template.render(prms)
    log.debug(f"> {name} --> context for templates == {prms}")
    with open(str(outpath), "w") as outfile:
        outfile.write(outcome)
    log.debug(f"> {name} --> processed ontlogy written to '{outpath}'")

    nspub = dict(error=True)  # this assumes things will go bad :)
    try:                      # apply pylode
        od = OntDoc(outpath)
        log.debug(f"> {name} --> ontology loaded to pylode from '{outpath}'")
        # ask pylode to make the html
        od.make_html(destination=outhtmlpath, include_css=False)
        log.debug(f"> {name} --> html produced to '{outhtmlpath}'")
        # also add an extra copy from name.html to name/index.html AND for the css as well
        shutil.copy(outhtmlpath, outindexpath)
        shutil.copy(outhtmlpath.parent / "pylode.css", outindexpath.parent / "pylode.css")
        log.debug(f"> {name} --> copy added to '{outindexpath}'")
        # get some minimal metadata from the ttl since pylode loaded that into memory anyway?
        nspub = extract_pub_dict(od)  # if we got here however, things should be ok
        log.debug(f"> {name} --> ready with result == {nspub}")
        nspub['name'] = name
        nspub['relref'] = str(outindexpath.parent.relative_to(outfolder)).replace("\\", "/")
    except PylodeError as ple:
        log.error(f"> {name} --> pylode v.{plv} failed to process ontology at '{nspath}'")
        log.exception(ple)
    except Exception as e:
        log.error(f"> {name} --> unexpected failure in processing ontology at '{nspath}'")
        log.exception(e)
    finally:
        # return the pub struct with core elements for the overview page
        log.debug(f"> {name} --> returning result == {nspub}")
        return nspub

def publish_misc(baseuri, nsfolder, outfolder ):
    otherfiles = ["CNAME"]
    nsfolder = Path(nsfolder)
    outfolder = Path(outfolder)
    for other in otherfiles:
        otherfile = nsfolder / other
        if otherfile.exists():
            shutil.copy(otherfile, outfolder / other)
    #TODO consider generating CNAME file with content derived from baseuri

def publish_combined_index(baseuri, nsfolder, outfolder, logconf=None):
    enable_logging(logconf)
    #default target folder to input folder
    outfolder = nsfolder if outfolder is None else outfolder
    outfolder = Path(outfolder).resolve()
    nsfolder = Path(nsfolder).resolve()
    log.debug(f"publishing combined index from '{nsfolder}' to '{outfolder}' while applying baseuri={baseuri}")
    
    processing_list = list()
    
    root_folder_name = outfolder.parts[-1]
    log.debug(f"root folder name is {root_folder_name}")
    #run over nsfolder and process ontology files
    for folder, dirs, nsfiles in os.walk(outfolder, topdown=False, followlinks=True):
        for nsname in nsfiles:
            parent_folder = Path(folder).parts[-1]
            nssub = Path(folder).relative_to(outfolder)
            if parent_folder == root_folder_name:
                continue
            if nsname.endswith(".html"):
                #check if the name contains _vocab
                if nsname.endswith("_vocab.html"):
                    prsnt = False
                    for item in processing_list:
                        if item["folder"] == parent_folder:
                            item["vocabularies"] = nsname
                            break
                    if not prsnt:
                        processing_list.append({"folder":parent_folder, "ontologies":"", "vocabularies":nsname, "nssub":nssub})
                    continue
                #go voer processing list and check if the parent folder is already present in the folder key of the dict
                prsnt = False
                for item in processing_list:
                    if item["folder"] == parent_folder:
                        item["ontologies"] = nsname
                        prsnt = True
                        break
                if not prsnt:
                    processing_list.append({"folder":parent_folder, "ontologies":nsname, "vocabularies":"", "nssub":nssub})
                
                
                #take the last part of the folder 
                log.debug(f"parent_folder={parent_folder}")
                log.debug(f"processing {nsname} in {folder} in dir {dirs}")
    #clear out processing list by comparing the folder key and checking if each dict with the same folder name has a value is bot vocabulary and ontology
    for item in processing_list:
        if item["ontologies"] == "" and item["vocabularies"] != "":
            processing_list.remove(item)
    
    #run over the processing list and create the combined index
    #init result sets
    combined = dict()
    combined_in_err = set()
    for item in processing_list:
        nscombined = combined_index_pub(baseuri, nsfolder, item["nssub"], item["ontologies"], outfolder, item["ontologies"], item["vocabularies"])
        if nscombined["error"]:
            log.error(f"failed to process combined index for {item['folder']}")
            log.error(f"error message: {nscombined['error_message']}")
            combined_in_err.add(item["folder"])
        combined[item["folder"]] = nscombined
    return combined
        

def combined_index_pub(baseuri, nsfolder, nssub, nsname, outfolder, ontology, vocabulary):
    log.debug(f"combined index to process: {nssub}/{nsname} in {nsfolder}")
    log.debug(f"other params: baseuri={baseuri}, outfolder={outfolder}/{nssub}, ontology={ontology}, vocabulary={vocabulary}")
    toreturn = dict()
    try:
        # generate a proper index.html file using an embedded jinja-template
        prms = dict(ontology=ontology, baseuri=baseuri, vocabulary=vocabulary, nsname=nsname, nssub=nssub)
        templates_env = Environment(loader=BaseLoader)
        template = templates_env.from_string(EMBEDDED_INDEX_IFRAME_TEMPLATE)
        outcome = template.render(prms)
        log.debug(f"> INDEX --> context for template == {prms}")
        outindexpath = outfolder / nssub / "index.html"
        with open(str(outindexpath), "w") as outfile:
            outfile.write(outcome)
        log.debug(f"> INDEX --> overview of processed combined index written to '{outindexpath}'")
        toreturn["error"] = False
    except Exception as e:
        toreturn["error"] = True
        log.debug(f"> INDEX --> error while processing combined index for {nssub}/{nsname}")
        log.error(e)
        toretrun["error_message"] = str(e)
    finally:
        return toreturn
    
    
                
                

    
def vocabpub(baseuri, nsfolder, nssub, nsname, outfolder,template_path):
    log.debug(f"vocab to process: {nssub}/{nsname} in {nsfolder}")
    log.debug(f"other params: baseuri={baseuri}, outfolder={outfolder}")
    toreturn = dict()
    try:
        output_name_html = nsname.replace(".csv", "_vocab.html")
        output_name_ttl = nsname.replace(".csv", "_vocab.ttl")
        template_path = template_path
        template_name_html = "template_html.html"
        template_name_ttl = "template_ttl.ttl"
        input_file = nsfolder / nssub / nsname
        log.debug(f"input_file={input_file}")
        
        #check if the output folder exists, if not create it
        folder_name = nsname.replace(".csv", "")
        output_folder = outfolder / nssub /folder_name
        log.debug(f"output_folder={output_folder}")
        if not output_folder.exists():
            output_folder.mkdir(parents=True)
        
        #html generation
        args = {
            "input":input_file.__str__(),
            "output":(output_folder / output_name_html).__str__(),
            "template_path":template_path,
            "template_name":template_name_html
        }
        log.debug(f"arguments_pysubytd={args}")
        service = JinjaBasedGenerator(args["template_path"])
        source = {"_": SourceFactory.make_source(args["input"])}
        sink = SinkFactory.make_sink(args["output"], force_output=True)
        settings = Settings()
        service.process(args["template_name"], source, settings, sink)
        #ttl generation
        second_args = {
            "input":input_file.__str__(),
            "output":(output_folder / output_name_ttl).__str__(),
            "template_path":template_path,
            "template_name":template_name_ttl
        }
        log.debug(f"arguments_pysubytd={second_args}")
        service = JinjaBasedGenerator(second_args["template_path"])
        source = {"_": SourceFactory.make_source(second_args["input"])}
        sink = SinkFactory.make_sink(second_args["output"], force_output=True)
        service.process(second_args["template_name"], source, settings, sink)
        
        toreturn["error"] = False
    except Exception as e:
        toreturn['error'] = True
        toreturn['error_message'] = str(e)
    finally:
        return toreturn
    
    
def publish_vocabs(baseuri, nsfolder, outfolder, template_path,logconf=None):
    enable_logging(logconf)
    
    #default target folder to input folder
    outfolder = nsfolder if outfolder is None else outfolder
    outfolder = Path(outfolder).resolve()
    nsfolder = Path(nsfolder).resolve()
    log.debug(f"publishing vocabs from '{nsfolder}' to '{outfolder}' while applying baseuri={baseuri}")
    
    #init result sets
    vocabs = dict()
    vocabs_in_err = set()
    
    #run over nsfolder and process ontology files
    for folder, dirs, nsfiles in os.walk(nsfolder, topdown=False, followlinks=True):
        for nsname in nsfiles:
            if nsname.endswith(".csv"):
                log.debug(f"csv file at {folder} - {nsname} when walking {nsfolder}")
                
                nssub = Path(folder).relative_to(nsfolder)
                nskey  =f"{str(nssub)}/{nsname}"
                nspub = vocabpub(baseuri, nsfolder, nssub, nsname, outfolder, template_path)
                if nspub['error']:
                    log.debug(f"vocab {nskey} failed to publish")
                    log.exception(nspub['error_message'])
                    vocabs_in_err.add(nskey)
                vocabs[nskey] = nspub
                
    return vocabs

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
                nssub = Path(folder).relative_to(nsfolder)
                nskey = f"{str(nssub)}/{nsname}"
                nspub = ontopub(baseuri, nsfolder, nssub, nsname, outfolder)
                if bool(nspub.get("error")):  # if the error key is there and set to anything non-False
                    log.debug(f"error processing {nskey} --> {nspub}")
                    ontos_in_err.add(nskey)
                ontos[nskey] = nspub

    # copy any other stuff outside the actual pylode / ontology stuff 
    publish_misc(baseuri, nsfolder, outfolder)

    # generate a proper index.html file using an embedded jinja-template
    prms = dict(ontos=ontos, baseuri=baseuri)
    templates_env = Environment(loader=BaseLoader)
    template = templates_env.from_string(EMBEDDED_INDEX_TEMPLATE)
    outcome = template.render(prms)
    log.debug(f"> INDEX --> context for template == {prms}")
    outindexpath = outfolder / "index.html"
    with open(str(outindexpath), "w") as outfile:
        outfile.write(outcome)
    log.debug(f"> INDEX --> overview of processed ontologies written to '{outindexpath}'")

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
    #load in logconf
    enable_logging(logconf)
    myfolder = Path(__file__).parent.absolute()
    template_path = myfolder / "templates"
    log.debug(f"template_path={template_path} -- exists? {template_path.exists()}")

    # do the actual work
    # TODO consider some way to deal with the possible OntoPubException
    ontos = publish_ontologies(baseuri, nsfolder, outfolder, logconf)
    vocabs= publish_vocabs(baseuri, nsfolder, outfolder, template_path ,logconf)

    # function ehre that will genreate an index.html file with iframes for the ontology and for the possible vocabularies
    publish_combined_index(baseuri, nsfolder, outfolder, logconf)
    
    # set the action outputs
    print(f"::set-output name=ontologies::{ontos.keys()}")
    print(f"::set-output name=vocabs::{vocabs.keys()}")


if __name__ == "__main__":
    main()
