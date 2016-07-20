# Cinder Documentation
The bundled Cinder source files includes documentation that you can view locally. You can find the online version [here](https://libcinder.org/docs). If you are cloning the Cinder GitHub repo, the docs will need to be generated in your cloned local repo. This is a 2-step process.

The build process requires Python 2.7 and [Doxygen](www.doxygen.org/) 1.8.10, which can be downloaded from [the doxygen website](http://www.stack.nl/~dimitri/doxygen/) or installed via [homebrew](http://brew.sh/) on OS X.

## Building Cinder Docs

### Step 1: Doxygen Export
This step uses Doxygen to parse the cinder source and build out a directory of xml files and a **cinder.tag** file. You can either use the DoxyWizard Gui or the Doxygen CLI.


### Using DoxyWizard
The Cinder documentation pipeline supports [Doxywizard 1.8.10](http://www.stack.nl/~dimitri/doxygen/download.html#srcbin).

* Once you have Doxywizard installed, use it to open **docs/doxygen/Doxyfile**.
* Select the run tab
* Click "Run doxygen"

![Doxygen](htmlsrc/guides/docs/images/doxygen.png "Doxygen")

### Using Doxygen CLI
* Install [Doxygen](www.doxygen.org/) via homebrew
```sh
$ brew install doxygen
```
* From _docs/doxygen_ run:
```sh
$ doxygen Doxyfile
```



### Step 2: Docs HTML File Generation
This next step generates the documentation from newly generated Doxygen output. It requires that you have python 2.7.x to run it.

Open up your command line of choice
run ```python generateDocs.py```

![Doxygen](htmlsrc/guides/docs/images/terminal.png "Doxygen")

This process generates html files in the html directory. If the python file throws an error that results in incomplete docs, you can [file a GitHub issue](https://github.com/cinder/Cinder/issues/). Your docs will be available at **docs/index.html** in a local browser.


## Editing Cinder Docs

### Stylesheets
Compiled stylesheets are included in _htmlsrc/\_assets/css_. [Stylus](http://learnboost.github.io/stylus/) is the CSS preprocessor of choice, which can be installed via [`npm`](https://www.npmjs.com/).

* Install [`npm`](https://www.npmjs.com/) via homebrew
```sh
$ brew install npm
```
* Install stylesheet-building dependencies; from _docs/stylesrc_ run:
```sh
$ npm install
```
* Build stylesheets; from _docs/stylesrc_ run:
```sh
$ ./node_modules/.bin/gulp build
```

For more details on Cinder Docs read the [Building Docs](htmlsrc/guides/docs/building_docs.html) and [Documenting Cinder](htmlsrc/guides/docs/documenting_cinder.html) Guides.
