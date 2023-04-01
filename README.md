# Kitsu for Docker

**Docker compose for [Kitsu](https://kitsu.cg-wire.com/)**

### *This readme contains info for both Kitsu-for-Docker and Zou-for-Docker as it's most likely you wish to run both*


# Getting Started

Check out the [docker-compose.yaml](docker-compose.yaml) file in the repo for the setup.

Modify the [.env](.env) file as needed for your setup.

Place the [db/pg_ctl.conf](db/pg_ctl.conf) at `./db/pg_ctl.conf` from your docker-compose.yaml location or modify the docker-compose to match the location.


# Usage

On first run the installation will download your wanted Zou version.
It will then initialize and populate the database and create a `initialized.txt` file in your previews folder. This is done to make sure the initializion is done only ones.
If something goes wrong on your first launch, delete this file to re-initialize the database, else **never delete this file!**
A default admin account will also be created:

- login: admin@example.com
- password: mysecretpassword


# Zou commands

If you need to run any specific zou commands, open the terminal of cgwire-zou-app and enter your command.
You can run `zou --help` to see all available commands.


# Update database schema

If you need to update the zou database schema, open the terminal of cgwire-zou-app and enter `./upgrade_zou.sh`.


# For development

This project isn't built for development of Kitsu and Zou.
For that I highly recommend Mathieu Bouzard's version that you can find here: https://gitlab.com/mathbou/docker-cgwire/


# About authors

This project is based on Mathieu Bouzard's work as a base. You'll find his project at https://gitlab.com/mathbou/docker-cgwire/

Those Dockerfiles are based on CG Wire work, a company based in France. They help small
to midsize CG studios to manage their production and build a pipeline
efficiently.

They apply software craftsmanship principles as much as possible. They love
coding and consider that strong quality and good developer experience matter a lot.
Through their diverse experiences, they allow studios to get better at doing
software and focus more on  artistic work.

Visit [cg-wire.com](https://cg-wire.com) for more information.

[![CGWire Logo](https://zou.cg-wire.com/cgwire.png)](https://cgwire.com)