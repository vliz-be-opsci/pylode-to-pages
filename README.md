# pylode-to-pages

GitHub Action to apply [pylode](https://pypi.org/project/pyLODE/) for publishing github-managed ontologies via github pages


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

## Kick-start the thing

In order to get this thing flying one needs to run these steps as an admin user on the github-project holding the ontologies to publish.

```
git checkout gh-pages
git push origin --delete gh-pages
git push origin
git checkout main
```

The motivation behind this can be [found here](https://github.com/peaceiris/actions-gh-pages#%EF%B8%8F-first-deployment-with-github_token) and [here](https://github.com/peaceiris/actions-gh-pages/issues/9).
