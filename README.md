# pylode-to-pages

GitHub Action to apply [pylode](https://pypi.org/project/pyLODE/) for publishing github-managed ontologies via github pages

## Status

[![build](https://github.com/vliz-be-opsci/pylode-to-pages/actions/workflows/build.yml/badge.svg)](https://github.com/vliz-be-opsci/pylode-to-pages/actions/workflows/build.yml)
[![release](https://badgen.net/github/release/vliz-be-opsci/pylode-to-pages)](https://github.com/vliz-be-opsci/pylode-to-pages/releases)

## Working
This action is to be used on git projects that maintain described ontology-files in ttl. It applies pyLODE to convert a human readable html version of them to be published via github pages.

The generated html is placed inside the actual repository folder `./` using this procedure:
* It simply runs through all folders and files and looks for `**/name.ttl` files.
* For all found entries it
  * creates a backup `**/name.ttl.bak` file
  * uses jinja2 to pre-process those to inject the provided `{{ baseuri }}` and `{{ name }}` parameters to update the `**/name.ttl` file
  * using pyLODE it produces an html file called `**/name` from the contents of the ttl
  * and finally adds an entry for it in the `./index.html`  at the root



## Writing your ontologies

The jinja2 pre-processing allows to have specific values to be injected:

| parameter | contents                                     |
| --------- | ---------------------------------------------|
| baseuri   | url to be used in publishing, passed via action-yaml file (see below) |
| name      | name of the current ttl being processed      |


## Enabling the action for your NS-ontology-project

Below is an example yaml file that once copied to `/.github/workflow/pylode_to_pages.yml` will trigger the publishing to github pages action on push to the "main" branch.

```yml

name: PyLODE to GitHub Pages
on:
  push:
    branches:
      - main  # Set a branch name to trigger deployment
  pull_request:
jobs:
  pylode-to-pages:
    runs-on: ubuntu-20.04
    concurrency:
      group: ${{ github.workflow }}-${{ github.ref }}
    steps:
      - uses: actions/checkout@v2
        with:
          submodules: true  # Fetch Hugo themes (true OR recursive)
          fetch-depth: 0    # Fetch all history for .GitInfo and .Lastmod

      - name: Setup Python
        uses: actions/setup-python@v3
        with:
          python-version: '3.x'

      - name: Build Pages
        uses: vliz-be-opsci/pylode-to-pages@v0
        with:
          baseuri: http://yourdomain.com/NS/

      - name: Deploy
        uses: peaceiris/actions-gh-pages@v3
        if: ${{ github.ref == 'refs/heads/main' }}
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./
```

## Action Configuration Options

The action supports the following input parameters:

| Parameter | Description | Required | Default |
|-----------|-------------|----------|---------|
| `baseuri` | URL base of the domain where this ontology gets published | Yes | - |
| `nsfolder` | Path to the ontologies to be processed | No | `.` |
| `outfolder` | Path to where results should be placed | No | `.` |
| `logconf` | Log configuration file in YAML format | No | `logconf.yml` |
| `ignore_folders` | Comma-separated list of folder paths to ignore during processing | No | `` |

### Using the ignore_folders parameter

The `ignore_folders` parameter allows you to exclude certain folders from being processed by the action. This is useful for:
- Excluding test directories
- Skipping documentation folders
- Ignoring version control folders
- Avoiding processing of work-in-progress ontologies

**Example with ignore_folders:**

```yml
- name: Build Pages
  uses: vliz-be-opsci/pylode-to-pages@v0
  with:
    baseuri: http://yourdomain.com/NS/
    ignore_folders: 'tests,docs,.git,drafts'
```

In this example, any `.ttl` or `.csv` files found in folders named `tests`, `docs`, `.git`, or `drafts` (at any level in the directory tree) will be skipped during processing.

**Advanced configuration example:**

```yml
- name: Build Pages
  uses: vliz-be-opsci/pylode-to-pages@v0
  with:
    baseuri: http://yourdomain.com/NS/
    nsfolder: ./ontologies
    outfolder: ./public
    ignore_folders: 'tests,examples,deprecated'
    logconf: ./config/logging.yml
```

## Kick-start the thing

In order to get this thing flying one needs to run these steps as an admin user on the github-project holding the ontologies to publish.

```
git checkout gh-pages
git push origin --delete gh-pages
git push origin
git checkout main
```

The motivation behind this can be [found here](https://github.com/peaceiris/actions-gh-pages#%EF%B8%8F-first-deployment-with-github_token) and [here](https://github.com/peaceiris/actions-gh-pages/issues/9).

## Error Handling and Debugging

The action provides detailed error messages when processing fails. When an error occurs:

1. **Check the Action Logs**: The action logs will show which ontologies or vocabularies failed to process
2. **Review Error Details**: Each error includes:
   - The file that failed to process
   - The specific error message from PyLODE or the processing pipeline
   - A stack trace for debugging

**Common Issues:**

- **Invalid TTL Syntax**: If your ontology file has syntax errors, PyLODE will fail with a parsing error
- **Missing Dependencies**: Ensure all referenced namespaces and imports are accessible
- **Path Issues**: Verify that `nsfolder` and `outfolder` paths are correct

**Example Error Output:**

```
ERROR: Error processing ontology ./myontology.ttl
ERROR: Error details: Pylode error: Unable to parse RDF file
ERROR: Failed to process 1 out of 3 ontologies
ERROR:   - ./myontology.ttl
```

To get more detailed logging, you can provide a custom log configuration file via the `logconf` parameter.
