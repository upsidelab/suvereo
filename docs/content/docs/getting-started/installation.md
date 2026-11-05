# Installation

The quickest way to run Suvereo is the [Suvereo starter](/docs/customization/using-the-suvereo-starter): a repository that starts the server and frontend with Docker Compose and gives you a place for your own code. A working instance takes a few minutes to set up.

## Setting up with Docker Compose

Clone the starter and create the configuration files from the samples:

```shell
git clone https://github.com/upsidelab/suvereo-starter
cd suvereo-starter
cp server/config/sample.env server/config/.env
cp frontend/config/sample.env frontend/config/.env
```

The default configuration uses the OpenAI API for generating embeddings and for the language model. Set your key in `server/config/.env`:

```
OPENAI_API_KEY=...
```

Then build and start the environment:

```shell
docker compose build && docker compose up
```

The starter comes with a diet advice [vertical](/docs/concepts#vertical) as a working example. It is not required: you can replace it with your own, as described on the [starter page](/docs/customization/using-the-suvereo-starter).

## Accessing the admin panel

Once the containers are running, open the application at [http://localhost:10001](http://localhost:10001). The API is at [http://localhost:10000](http://localhost:10000).

Sign in as the initial admin user. By default:

**Email**: admin@example.com

**Password**: changeme

The admin user is created only on the first start, when the database has no users. To use other credentials, set `ECL_ADMIN_EMAIL` and `ECL_ADMIN_PASSWORD` in `server/config/.env` before that first start. Changing them later does not affect an existing database: change the password in the app, or reset the database with `docker compose down -v`. Replace the defaults for any instance that is not purely local.

Environment files are read when a container is created. After editing one, run `docker compose up -d --force-recreate`.

## Next steps

- Learn how [data sets, users and permissions](/docs/management) are managed.
- Define your own domain with the [Suvereo starter](/docs/customization/using-the-suvereo-starter) and the [tutorial](/docs/customization/tutorial).
