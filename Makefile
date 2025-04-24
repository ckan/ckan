.DEFAULT_GOAL := help
.PHONY: help copy-vendor

FORCE:

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'


changelog-% documentation-% hljs-% translation-% vendor-%: FORCE

###############################################################################
#                               Release process                               #
###############################################################################
frontend-build:  ## compile front-end SCSS sources into CSS
	npm run build

translation-extract:  ## extract new strings from CKAN source into .pot file
	python setup.py extract_messages

translation_minimal_completeness = 5
translation-pull: ## get the latest translations from Transifex
	tx pull --all --minimum-perc=$(translation_minimal_completeness) --force

translation-update:  ## update .po files with new strings from .pot
	python setup.py update_catalog --no-fuzzy-matching

translation-check-format:  ## locate format errors inside translation files
	find ckan/i18n/ -name "*.po"| xargs -n 1 msgfmt -c

translation-push: ## send compiled translations to Transifex
	tx push --source --translations --force

translation-compile: ## update .mo file by compiling .po files
	python setup.py compile_catalog

documentation-build:  ## compile the documentation
	rm -rf build/sphinx
	sphinx-build doc build/sphinx

changelog-view:  ## check output of changelog compilations without actual changes
	towncrier build --draft

changelog-build: ## compile changelog and remove changelog fragments that are no longer needed
	towncrier build --yes

###############################################################################
#                          Front-end vendor libraries                         #
###############################################################################

# vendors mentioned here will be copied via global `vendor-copy` task
vendor_names = jquery bootstrap moment fa jquery-fileupload qs dompurify popover hljs htmx
# common folder for all vendor libraries
vendor_dir = ckan/public/base/vendor

vendor-list:  ## show all available front-end vendor names
	@echo 'Every vendor <NAME> listed below can be individually copied into public CKAN folder via `make vendor-copy-<NAME>` command:'
	@for name in $$(echo $(vendor_names) | xargs -n1 | sort); do echo -e "\t$$name"; done

vendor-copy: $(vendor_names:%=vendor-copy-%) ## copy front-end dependencies from node_modules into public CKAN folders

vendor-copy-jquery:
	cp node_modules/jquery/dist/jquery.js	$(vendor_dir)/

vendor-copy-bootstrap:
	cp -rf node_modules/bootstrap/scss/* $(vendor_dir)/bootstrap/scss/
	cp -rf node_modules/bootstrap/js/dist/* $(vendor_dir)/bootstrap/js/
	cp -rf node_modules/bootstrap/dist/js/* $(vendor_dir)/bootstrap/js/

vendor-copy-moment:
	cp node_modules/moment/min/moment-with-locales.js $(vendor_dir)/

vendor-copy-fa:
	cp node_modules/@fortawesome/fontawesome-free/css/all.min.css $(vendor_dir)/fontawesome-free/css/all.css
	cp node_modules/@fortawesome/fontawesome-free/webfonts/* $(vendor_dir)/fontawesome-free/webfonts/

vendor-copy-jquery-fileupload:
	cp node_modules/blueimp-file-upload/js/*.js $(vendor_dir)/jquery-fileupload/

vendor-copy-qs:
	cp node_modules/qs/dist/qs.js $(vendor_dir)/

vendor-copy-dompurify:
	cp node_modules/dompurify/dist/purify.js $(vendor_dir)/

vendor-copy-popover:
	cp node_modules/@popperjs/core/dist/cjs/popper.js $(vendor_dir)/

vendor-copy-hljs: hljs-build
	cp node_modules/highlight.js/build/highlight.js $(vendor_dir)/hljs/
	cp node_modules/highlight.js/build/demo/styles/a11y-light.css $(vendor_dir)/hljs/a11y-light.css
	cp node_modules/highlight.js/build/demo/styles/a11y-dark.css $(vendor_dir)/hljs/a11y-dark.css

vendor-copy-htmx:
	cp node_modules/htmx.org/dist/htmx.js $(vendor_dir)/

###############################################################################
#                                 Highlight.js                                #
###############################################################################
hljs-prepare:  ## install Highlight.js build dependencies
ifeq ($(wildcard node_modules/highlight.js/tools),)
	@echo 'Wrong version of highlight.js installed. Update dependencies via `npm ci`'
else ifeq ($(wildcard node_modules/highlightjs-curl),)
	@echo 'highlightjs-curl is not installed. Update dependencies via `npm ci`'
else ifeq ($(wildcard node_modules/highlight.js/node_modules/clean-css),)
	npm explore highlight.js -- npm i
	npm explore highlight.js -- cp ../highlightjs-curl/src/languages/curl.js src/languages/
endif
	@echo 'highligh.js build dependencies are installed'

hljs_languages = javascript powershell r python json xml bash
hljs-build: hljs-prepare ## build Highlight.js for languages specified by `hljs_languages` variable
	@echo "Building highlight.js for the following targets: $(hljs_languages)"
	@echo 'Different targets can be set via hljs_languages variable: make $@ hljs_languages="cs curl dart php"'
	npm explore highlight.js -- node tools/build.js $(hljs_languages)
