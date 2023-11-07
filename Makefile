.DEFAULT_GOAL := help
.PHONY: help copy-vendor

FORCE:

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'


copy-vendor-%: FORCE

###############################################################################
#                          Front-end vendor libraries                         #
###############################################################################
vendor_names = jquery bootstrap moment fa jquery-fileupload qs dompurify popover hljs htmx
vendor_dir = ckan/public/base/vendor

copy-vendors: $(vendor_names:%=copy-vendor-%) ## copy front-end dependencies from node_modules into public CKAN folders

copy-vendor-jquery:
	cp node_modules/jquery/dist/jquery.js	$(vendor_dir)/

copy-vendor-bootstrap:
	cp -rf node_modules/bootstrap/scss/* $(vendor_dir)/bootstrap/scss/
	cp -rf node_modules/bootstrap/js/dist/* $(vendor_dir)/bootstrap/js/
	cp -rf node_modules/bootstrap/dist/js/* $(vendor_dir)/bootstrap/js/

copy-vendor-moment:
	cp node_modules/moment/min/moment-with-locales.js $(vendor_dir)/

copy-vendor-fa:
	cp node_modules/@fortawesome/fontawesome-free/css/all.css $(vendor_dir)/fontawesome-free/css/
	cp node_modules/@fortawesome/fontawesome-free/webfonts/* $(vendor_dir)/fontawesome-free/webfonts/

copy-vendor-jquery-fileupload:
	cp node_modules/blueimp-file-upload/js/*.js $(vendor_dir)/jquery-fileupload/

copy-vendor-qs:
	cp node_modules/qs/dist/qs.js $(vendor_dir)/

copy-vendor-dompurify:
	cp node_modules/dompurify/dist/purify.js $(vendor_dir)/

copy-vendor-popover:
	cp node_modules/@popperjs/core/dist/cjs/popper.js $(vendor_dir)/

copy-vendor-hljs:
	cp node_modules/@highlightjs/cdn-assets/highlight.js ckanext/textview/assets/vendor/
	cp node_modules/@highlightjs/cdn-assets/highlight.js ckanext/datastore/assets/vendor
	cp node_modules/@highlightjs/cdn-assets/styles/a11y-light.min.css ckanext/textview/assets/styles/a11y-light.css
	cp node_modules/@highlightjs/cdn-assets/styles/a11y-dark.min.css ckanext/datastore/assets/vendor/a11y-dark.css

copy-vendor-htmx:
	cp node_modules/htmx.org/dist/htmx.js $(vendor_dir)/
