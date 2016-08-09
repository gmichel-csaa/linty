# [Linty](https://www.lintyapp.com)
[![Stories in Ready](https://badge.waffle.io/ZeroCater/linty.png?label=ready&title=Waffle)](https://waffle.io/ZeroCater/linty)
[![CircleCI](https://circleci.com/gh/ZeroCater/linty.svg?style=svg)](https://circleci.com/gh/ZeroCater/linty)
[![Coverage Status](https://coveralls.io/repos/github/ZeroCater/linty/badge.svg?branch=master)](https://coveralls.io/github/ZeroCater/linty?branch=master)
[![Linty](https://linty.herokuapp.com/repo/ZeroCater/linty/badge.svg)](https://linty.herokuapp.com/repo/ZeroCater/linty)

[Linty](https://www.lintyapp.com) is _Linting as a Service_. Users can sign in with Github, select a repo, and immediately get linting for their code.

Features:
* One click repo registration/de-registration
* Pass/Fail statuses on Pull Requests
* History of lint results
* Pass/Fail Badges for your READMEs
* Proper permissions for private repos

The app is live at [lintyapp.com](https://www.lintyapp.com).

### Development

To get linty running locally for development, you'll need a few things:
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
