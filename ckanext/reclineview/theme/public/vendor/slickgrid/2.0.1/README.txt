This compiled version of SlickGrid has been obtained with the Google Closure
Compiler, using the following command:

java -jar compiler.jar --js=slick.core.js --js=slick.grid.js --js=slick.editors.js --js_output_file=slick.grid.min.js

There are two other files required for the SlickGrid view to work properly:

 * jquery-ui-1.8.16.custom.min.js 
 * jquery.event.drag-2.0.min.js

These are included in the Recline source, but have not been included in the
built file to make easier to handle compatibility problems.

Please check SlickGrid license in the included MIT-LICENSE.txt file.

[1] https://developers.google.com/closure/compiler/
