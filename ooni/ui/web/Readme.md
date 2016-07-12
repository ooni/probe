# Development instructions for OONI web UI

The OONI web UI is based on the following main components:

* [klein](https://klein.readthedocs.org/) for the backend API routing

* [angular.js](https://angularjs.org/) as the frontend web framework

* [webpack](https://webpack.github.io/) for building and dependency management

* [bootstrap](http://getbootstrap.com/) to make styling less painful

## Setting up a development environment

You are expected to already have a working python development environment that
allows you to develop ooni-probe.

In here are listed only the extra steps that are specific to the web UI.

The dependencies of the web UI are all managed via `npm` and they can be
installed with:

```
npm install
```

This requires that you have a recent version of
[node](https://nodejs.org/en/download/).

## Code architecture

The web UI is highly modular and is based around the concept of angular
components.
The reason for doing this is that these components can then be re-used across
the various web based graphical interfaces that need to work with OONI data,
such as ooni-explorer, net-probe, ooni-web, etc.

The boilerplate code for a component can be found inside of
`data/component-template/`.

It consists of the following items:

* xxx.component.js this is the actual [angular
  component](https://docs.angularjs.org/guide/component) that includes
  a template, a controller and a stylesheet

* xxx.controller.js this is the [angular
  controller](https://docs.angularjs.org/guide/controller) for the component in
  question. Put in here all the logic necessary for creating variables that are
  to be inside of the scope of the template and registering functions that can
  be called from inside the template.
  Do not use this for manipulating DOM, sharing code across components.

* xxx.css this is the style-sheet for the component in question (XXX in the
  future we may want to use some other templating language such as less, sass
  or whatever people use these days to make our life easier)

* xxx.html this is the HTML template for the component. Refer to the
  [angular.js documentation on
  templates](https://docs.angularjs.org/guide/templates) to learn more about
  what you can do with it.

* xxx.js this is the glue that brings all of the above together. In particular
  what we do inside of here is setting up the URL routes for the particular
  component and setting the component name.
  This is the actual entry point for the component.

## Tips for developing

In order to build the web UI you should run the following command:

```
npm build
```

This will generate the bundled web application inside of `ooni/ui/web/build`.

To serve it via ooniprobe for development purposes you should run:

```
PYTHONPATH=`pwd` python -m ooni.ui.web.web
```

Note: this workflow is probably going to change in the very near future

The `setup.py` includes a custom command for creating all the boilerplate code
required for creating a new component.
It requires `jinja2` that should already be installed as part of klein, but if
you are getting some errors related to that try installing it (XXX remove this
when we figure out if it's actually needed).

This can be invoked by running:

```
python setup.py generate_component
```

It will then ask you to input a component name and it will automatically
populate the directory `ooni/ui/web/client/app/components/[you-name]` with
the scaffolding for your new component.
