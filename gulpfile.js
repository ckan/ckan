const path = require("path");
const { src, watch, dest, parallel } = require("gulp");
const sass = require("gulp-sass")(require("sass"));
const if_ = require("gulp-if");
const sourcemaps = require("gulp-sourcemaps");
const rename = require("gulp-rename");

const with_sourcemaps = () => !!process.env.DEBUG;
const renamer = (path) => {
  const variant = process.argv[3];
  if (variant) {
    // convert main/main-rtl into green/green-rtl
    path.basename = path.basename.replace("main", variant.slice(2));
  }
  return path;
};

const build = () =>
  src([
    __dirname + "/ckan/public/base/scss/main.scss",
    __dirname + "/ckan/public/base/scss/main-rtl.scss",
  ])
    .pipe(if_(with_sourcemaps(), sourcemaps.init()))
    .pipe(sass({ outputStyle: 'expanded' }).on('error', sass.logError))
    .pipe(if_(with_sourcemaps(), sourcemaps.write()))
    .pipe(rename(renamer))
    .pipe(dest(__dirname + "/ckan/public/base/css/"));

const watchSource = () =>
  watch(
    __dirname + "/ckan/public/base/scss/**/*.scss",
    { ignoreInitial: false },
    build
  );

const jquery = () =>
  src(__dirname + "/node_modules/jquery/dist/jquery.js").pipe(
    dest(__dirname + "/ckan/public/base/vendor")
  );

const bootstrapScss = () =>
  src(__dirname + "/node_modules/bootstrap-sass/assets/**/*").pipe(
    dest(__dirname + "/ckan/public/base/vendor/bootstrap/")
  );

const moment = () =>
  src(__dirname + "/node_modules/moment/min/moment-with-locales.js").pipe(
    dest(__dirname + "/ckan/public/base/vendor")
  );

const fontAwesomeCss = () =>
  src(__dirname + "/node_modules/font-awesome/css/font-awesome.css").pipe(
    dest(__dirname + "/ckan/public/base/vendor/font-awesome/css")
  );

const fontAwesomeFonts = () =>
  src(__dirname + "/node_modules/font-awesome/fonts/*").pipe(
    dest(__dirname + "/ckan/public/base/vendor/font-awesome/fonts")
  );

const jQueryFileUpload = () =>
  src(__dirname + "/node_modules/blueimp-file-upload/js/*.js").pipe(
    dest(__dirname + "/ckan/public/base/vendor/jquery-fileupload/")
  );

const qs = () =>
  src(__dirname + "/node_modules/qs/dist/qs.js").pipe(
    dest(__dirname + "/ckan/public/base/vendor/")
  )

const highlightJs = () =>
  src(__dirname + "/node_modules/@highlightjs/cdn-assets/highlight.js").pipe(
    dest(__dirname + "/ckanext/textview/theme/public/vendor/")
  )

const highlightJsStyles = () =>
  src(__dirname + "/node_modules/@highlightjs/cdn-assets/styles/a11y-light.min.css").pipe(
    rename("a11y-light.css")).pipe(
    dest(__dirname + "/ckanext/textview/theme/public/styles/")
  )



exports.build = build;
exports.watch = watchSource;
exports.updateVendorLibs = parallel(
  jquery,
  bootstrapScss,
  moment,
  fontAwesomeCss,
  fontAwesomeFonts,
  jQueryFileUpload,
  qs,
  highlightJs,
  highlightJsStyles
);
