/* Sets up anchor elements that have the rel="external" attribute to open
 * in a new window or tab but setting the target property to the non-standard
 * "_blank" value.
 */
(function setExternalLinks() {
  var links = document.getElementsByTagName('a');
  var length = links.length;
  var index = 0;

  for (; index < length; index += 1) {
    if (links[index].getAttribute('rel') === 'external') {
      links[index].target = '_blank';
    }
  }
})();
