const path = require("path");
const { src, watch, dest, parallel } = require("gulp");
const scss = require("gulp-sass");
const if_ = require("gulp-if");
const sourcemaps = require("gulp-sourcemaps");
const rename = require("gulp-rename");

console.log(process.argv);
const with_sourcemaps = () => !!process.env.DEBUG;
const renamer = (path) => {
  if (process.argv[3]) {
    path.basename = process.argv[3].slice(1);
  }
  return path;
};

const build = () =>
  src(__dirname + "/ckan/public/base/scss/main.scss")
    .pipe(if_(with_sourcemaps(), sourcemaps.init()))
    .pipe(scss())
    .pipe(if_(with_sourcemaps(), sourcemaps.write()))
    .pipe(rename(renamer))
    .pipe(dest(__dirname + "/ckan/public/base/css/"));

const watchSource = () =>
  watch(
    __dirname + "/ckan/public/base/sass/**/*.scss",
    { ignoreInitial: false },
    build
  );

const jquery = () =>
  src(__dirname + "/node_modules/jquery/dist/jquery.js").pipe(
    dest(__dirname + "/ckan/public/base/vendor")
  );

const bootstrap = () =>
  src(__dirname + "/node_modules/bootstrap/dist/**/*").pipe(
    dest(__dirname + "/ckan/public/base/vendor/bootstrap")
  );

const bootstrapScss = () =>
  src(__dirname + "/node_modules/bootstrap/scss/**/*").pipe(
    dest(__dirname + "/ckan/public/base/vendor/bootstrap/scss")
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

const fontAwesomeScss = () =>
  src(__dirname + "/node_modules/font-awesome/scss/*").pipe(
    dest(__dirname + "/ckan/public/base/vendor/font-awesome/scss")
  );

const jQueryFileUpload = () =>
  src(__dirname + "/node_modules/blueimp-file-upload/js/*.js").pipe(
    dest(__dirname + "/ckan/public/base/vendor/jquery-fileupload/")
  );

exports.build = build;
exports.watch = watchSource;
exports.updateVendorLibs = parallel(
  jquery,
  bootstrap,
  bootstrapScss,
  moment,
  fontAwesomeCss,
  fontAwesomeFonts,
  fontAwesomeScss,
  jQueryFileUpload
);
