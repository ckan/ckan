const path = require("path");
const { src, watch, dest, parallel } = require("gulp");
const less = require("gulp-less");
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
    __dirname + "/ckan/public/base/less/main.less",
    __dirname + "/ckan/public/base/less/main-rtl.less",
  ])
    .pipe(if_(with_sourcemaps(), sourcemaps.init()))
    .pipe(less())
    .pipe(if_(with_sourcemaps(), sourcemaps.write()))
    .pipe(rename(renamer))
    .pipe(dest(__dirname + "/ckan/public/base/css/"));

const watchSource = () =>
  watch(
    __dirname + "/ckan/public/base/less/**/*.less",
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

const bootstrapLess = () =>
  src(__dirname + "/node_modules/bootstrap/less/**/*").pipe(
    dest(__dirname + "/ckan/public/base/vendor/bootstrap/less")
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

const fontAwesomeLess = () =>
  src(__dirname + "/node_modules/font-awesome/less/*").pipe(
    dest(__dirname + "/ckan/public/base/vendor/font-awesome/less")
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
  bootstrapLess,
  moment,
  fontAwesomeCss,
  fontAwesomeFonts,
  fontAwesomeLess,
  jQueryFileUpload
);
