import rdflib
import csv
from pathlib import Path
from jinja2 import Environment, FileSystemLoader


def ttl_to_csv(ttl_path):
    g = rdflib.Graph()
    with open(ttl_path, "r", encoding="utf8") as f:
        g.parse(f, format="ttl")

    base = None
    for s, p, o in g.triples((None, rdflib.namespace.RDF.type, None)):
        if isinstance(s, rdflib.URIRef):
            base = str(s).rsplit("#", 1)[0] + "#"
            break

    if base is None:
        raise ValueError("No base URI found in the TTL file.")

    rows = {}
    predicates = set()
    collection_row = None

    for s, p, o in g:
        if str(s) == "":
            id = base
        else:
            id = f"{base}{s.split(base)[-1]}"
        if id not in rows:
            rows[id] = {"ID": id, "type": None}
        if str(o) == "http://www.w3.org/2004/02/skos/core#Concept":
            rows[id]["type"] = "concept"
        elif str(o) == "http://www.w3.org/2004/02/skos/core#Collection":
            rows[id]["type"] = "collection"
            collection_row = rows[id]
            rows[id]["ID"] = base
        else:
            predicate = (
                str(p)
                .replace("//", "_")
                .replace(".", "_")
                .replace("/", "_")
                .replace(":", "_")
                .replace("#", "_")
            )
            rows[id][predicate] = str(o)
            predicates.add(predicate)

    output_path = Path(ttl_path).with_suffix(".csv")
    with open(output_path, "w", newline="", encoding="utf8") as csvfile:
        fieldnames = ["ID", "type"] + list(predicates)
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        if collection_row:
            writer.writerow(collection_row)
        for row in rows.values():
            if row != collection_row:
                writer.writerow(row)


def csv_to_html(csv_path, template_path, output_path):
    env = Environment(loader=FileSystemLoader("."))
    template = env.get_template(template_path)

    concepts = []
    collections = []

    with open(csv_path, "r", encoding="utf8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if row["type"] == "concept":
                concepts.append(row)
            elif row["type"] == "collection":
                collections.append(row)

    title = Path(output_path).stem

    html_content = template.render(
        concepts=concepts, collections=collections, title=title
    )

    with open(output_path, "w", encoding="utf8") as htmlfile:
        htmlfile.write(html_content)


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 3:
        print("Usage: python ttl_to_csv_to_html.py <path_to_ttl_file> <template_path>")
    else:
        ttl_to_csv(sys.argv[1])
        csv_path = Path(sys.argv[1]).with_suffix(".csv")
        output_html_path = Path(sys.argv[1]).with_suffix(".html")
        csv_to_html(csv_path, sys.argv[2], output_html_path)
