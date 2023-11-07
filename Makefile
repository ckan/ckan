.DEFAULT_GOAL := help
.PHONY: help copy-vendor

FORCE:

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'


release-% copy-vendor-%: FORCE

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

###############################################################################
#                          Front-end vendor libraries                         #
###############################################################################
vendor_names = jquery bootstrap moment fa jquery-fileupload qs dompurify popover hljs htmx
vendor_dir = ckan/public/base/vendor

vendor-list:  ## show all available front-end vendor names
	@echo 'Every vendor <NAME> listed below can be individually copied into public CKAN folder via `make vendor-copy-<NAME>` command:'
	@for name in $(vendor_names); do echo -e "\t$$name"; done

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
	cp node_modules/@fortawesome/fontawesome-free/css/all.css $(vendor_dir)/fontawesome-free/css/
	cp node_modules/@fortawesome/fontawesome-free/webfonts/* $(vendor_dir)/fontawesome-free/webfonts/

vendor-copy-jquery-fileupload:
	cp node_modules/blueimp-file-upload/js/*.js $(vendor_dir)/jquery-fileupload/

vendor-copy-qs:
	cp node_modules/qs/dist/qs.js $(vendor_dir)/

vendor-copy-dompurify:
	cp node_modules/dompurify/dist/purify.js $(vendor_dir)/

vendor-copy-popover:
	cp node_modules/@popperjs/core/dist/cjs/popper.js $(vendor_dir)/

vendor-copy-hljs:
	cp node_modules/@highlightjs/cdn-assets/highlight.js ckanext/textview/assets/vendor/
	cp node_modules/@highlightjs/cdn-assets/highlight.js ckanext/datastore/assets/vendor
	cp node_modules/@highlightjs/cdn-assets/styles/a11y-light.min.css ckanext/textview/assets/styles/a11y-light.css
	cp node_modules/@highlightjs/cdn-assets/styles/a11y-dark.min.css ckanext/datastore/assets/vendor/a11y-dark.css

vendor-copy-htmx:
	cp node_modules/htmx.org/dist/htmx.js $(vendor_dir)/
