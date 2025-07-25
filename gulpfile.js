const path = require("path");
const { src, watch, dest, parallel } = require("gulp");
const sass = require("gulp-sass")(require("sass"));
const if_ = require("gulp-if");
const sourcemaps = require("gulp-sourcemaps");
const rename = require("gulp-rename");

const with_sourcemaps = () => !!process.env.DEBUG || !!process.argv[4];
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

const buildMidnightBlue = () =>
  src([
    __dirname + "/ckan/public-midnight-blue/base/scss/main.scss",
    __dirname + "/ckan/public-midnight-blue/base/scss/main-rtl.scss",
    ])
    .pipe(if_(with_sourcemaps(), sourcemaps.init()))
    .pipe(sass({ outputStyle: 'expanded' }).on('error', sass.logError))
    .pipe(if_(with_sourcemaps(), sourcemaps.write()))
    .pipe(rename(renamer))
    .pipe(dest(__dirname + "/ckan/public-midnight-blue/base/css/"));

const watchMidnightBlue = () =>
  watch(
    __dirname + "/ckan/public-midnight-blue/base/scss/**/*.scss",
    { ignoreInitial: false },
    buildMidnightBlue
  );

const jquery = () =>
  src(__dirname + "/node_modules/jquery/dist/jquery.js").pipe(
    dest(__dirname + "/ckan/public/base/vendor")
  );

const bootstrapScss = () =>
  src([__dirname + "/node_modules/bootstrap/scss/**/*", ]).pipe(
    dest(__dirname + "/ckan/public/base/vendor/bootstrap/scss")
  );

const bootstrapJS = () =>
src([__dirname + "/node_modules/bootstrap/js/dist/**/*",
    __dirname + "/node_modules/bootstrap/dist/js/**/*"
  ]).pipe(dest(__dirname + "/ckan/public/base/vendor/bootstrap/js"));

const moment = () =>
  src(__dirname + "/node_modules/moment/min/moment-with-locales.js").pipe(
    dest(__dirname + "/ckan/public/base/vendor")
  );

const popOver = () =>
  src(__dirname + "/node_modules/@popperjs/core/dist/cjs/popper.js").pipe(
    dest(__dirname + "/ckan/public/base/vendor/")
);

const DOMPurify = () =>
  src(__dirname + "/node_modules/dompurify/dist/purify.js").pipe(
    dest(__dirname + "/ckan/public/base/vendor/")
);

const fontAwesomeCss = () =>
  src(__dirname + "/node_modules/@fortawesome/fontawesome-free/css/all.css").pipe(
    dest(__dirname + "/ckan/public/base/vendor/fontawesome-free/css")
  );

const fontAwesomeFonts = () =>
  src(__dirname + "/node_modules/@fortawesome/fontawesome-free/webfonts/*", {"encoding": false}).pipe(
    dest(__dirname + "/ckan/public/base/vendor/fontawesome-free/webfonts")
  );

const jQueryFileUpload = () =>
  src(__dirname + "/node_modules/blueimp-file-upload/js/*.js").pipe(
    dest(__dirname + "/ckan/public/base/vendor/jquery-fileupload/")
  );

const qs = () =>
  src(__dirname + "/node_modules/qs/dist/qs.js").pipe(
    dest(__dirname + "/ckan/public/base/vendor/")
  )

const htmx = () =>
  src(__dirname + "/node_modules/htmx.org/dist/htmx.js").pipe(
    dest(__dirname + "/ckan/public/base/vendor/")
  )

const select2 = () =>
  src([
      __dirname + "/node_modules/select2/dist/js/**/*.js",
      __dirname + "/node_modules/select2/dist/css/select2.css",
      "!" + __dirname + "/node_modules/select2/dist/js/select2.js",
      "!" + __dirname + "/node_modules/select2/dist/js/*.min.js",
    ],
    ).pipe(dest(__dirname + "/ckan/public/base/vendor/select2/")
  )

exports.build = build;
exports.watch = watchSource;

exports.buildMidnightBlue = buildMidnightBlue;
exports.watchMidnightBlue = watchMidnightBlue;
exports.updateVendorLibs = parallel(
  jquery,
  bootstrapScss,
  bootstrapJS,
  moment,
  fontAwesomeCss,
  fontAwesomeFonts,
  jQueryFileUpload,
  qs,
  DOMPurify,
  popOver,
  htmx,
  select2
);
