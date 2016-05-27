# linty
[![Stories in Ready](https://badge.waffle.io/birkholz/linty.png?label=ready&title=Waffle)](https://waffle.io/birkholz/linty)
[![CircleCI](https://circleci.com/gh/birkholz/linty.svg?style=svg)](https://circleci.com/gh/birkholz/linty)
[![Coverage Status](https://coveralls.io/repos/github/birkholz/linty/badge.svg?branch=master)](https://coveralls.io/github/birkholz/linty?branch=master)
[![Linty](https://linty.herokuapp.com/repo/birkholz/linty/badge.svg)](https://linty.herokuapp.com/repo/birkholz/linty)

Linty is _Linting as a Service_. Users can sign in with Github, select a repo, and immediately get linting for their code.

Features:
* One click repo registration/de-registration
* Pass/fail statuses on Pull Requests
* History of lint results

The app is live at [linty.herokuapp.com](https://linty.herokuapp.com). It's currently running on free dynos, so if the site hangs for a while when you first visit it, it's just the dynos waking up.

### Development

To get linty running locally for development, you'll need a few things:
* virtualenv/pyenv to stay sane
* PostgreSQL (I highly recommend [Postgres.app](http://postgresapp.com/) for Mac)

```bash
git clone https://github.com/birkholz/linty.git && cd linty
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

Issues and Pull Requests are welcome. There's still a lot left before this app is really ready for public use.