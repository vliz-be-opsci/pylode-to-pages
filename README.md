# pylode-to-pages

GitHub Action to apply [pylode](https://pypi.org/project/pyLODE/) for publishing github-managed ontologies via github pages


## Working
This action is to be used on git projects that maintain described ontology-files in ttl. It applies pyLODE to convert a human readable html version of them to be published via github pages.

The output site is produced in the relative `build-to-publish/` folder and follows this procedure:
* It simply runs through all folders and files and looks for `**name.ttl` files.
* For all found entries it
  * uses jinja2 to preprocess those to inject the provided {{ domain }} argument - being jinja2, you can choose to provide other interesting things
  * adds an entry for it in the `./index.html`  at the root
  * copies over the `**name.ttl` file to make it available for download
  * using pyLODE it produces an html file called `**name` from the contents of the ttl



## Writing your ontologies

The jinja2 pre-processing allows to have specific values to be injected




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
  deploy:
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
          baseurl: http://yourdomain.com/NS/

      - name: Deploy
        uses: peaceiris/actions-gh-pages@v3
        if: ${{ github.ref == 'refs/heads/main' }}
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./build-to-publish
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
