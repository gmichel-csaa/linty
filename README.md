# [Linty](https://www.lintyapp.com)
[![CircleCI](https://circleci.com/gh/ZeroCater/linty.svg?style=svg)](https://circleci.com/gh/ZeroCater/linty)
[![Coverage Status](https://coveralls.io/repos/github/ZeroCater/linty/badge.svg?branch=master)](https://coveralls.io/github/ZeroCater/linty?branch=master)
[![Linty](https://www.lintyapp.com/repo/ZeroCater/linty/badge.svg)](https://www.lintyapp.com/repo/ZeroCater/linty)

[Linty](https://www.lintyapp.com) is _Linting as a Service_. Users can sign in with Github, select a repo, and immediately get linting for their code.

Features:
* One click repo registration
* Pass/Fail statuses on Pull Requests
* History of lint results
* Pass/Fail Badges for your READMEs

The app is live at [lintyapp.com](https://www.lintyapp.com). Linty is still under heavy development, and is likely to change often and significantly. Things might break. Use with discretion.

### Setup

**Python**:

As long as you have a `requirements.txt` in the root of your project, Linty will run [pycodestyle](https://github.com/PyCQA/pycodestyle) against your project. You can configure pycodestyle using a `setup.cfg` file in the root of the project. See [ours](https://github.com/ZeroCater/linty/blob/master/setup.cfg) for an example.

**Javascript**:

JS linting is still relatively new. In order to lint a JS project, you'll need a `package.json` in the root of your project, and you'll need to define a `lint` script in it. This means you can have Linty run whatever linter you want, you just have to get it working locally first. Linty will install your linter like so: `npm install --ignore-scripts --only=dev`, so make sure you have all your linter dependencies in `devDependencies`. The linter will also need to return a non-zero status code when errors are found in order for Linty to register the run as a failure. There is no default linter for JS at the moment. Improvements to JS are coming.
Here's an example `package.json` for eslint:
```
{
  ...
  "scripts": {
    "lint:": "eslint .",
    ...
  },
  "devDependencies": {
    ...
    "eslint": "^2.13.1",
  }
}
```

### Development

To get linty running locally for development, you'll need a few things:
* Python 3
* virtualenv/pyenv to stay sane
* PostgreSQL (I highly recommend [Postgres.app](http://postgresapp.com/) for Mac)

```bash
git clone https://github.com/ZeroCater/linty.git && cd linty
pip install -r requirements.dev.txt
cp .env.sample .env

```

Edit `.env` as necessary.

```bash
python manage.py migrate
python manage.py runserver
```

You now have the server running!

### Contribution

Issues and Pull Requests are welcome.
You can view the development progress on Trello [here](https://trello.com/b/w6mQAxUG/linty)


### License

Linty is Copyright © 2016 ZeroCater. It is free software, and may be
redistributed under the terms specified in the [LICENSE](LICENSE) file.
