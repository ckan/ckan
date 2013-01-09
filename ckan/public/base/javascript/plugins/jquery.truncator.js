// HTML Truncator for jQuery
// by Henrik Nyh <http://henrik.nyh.se> 2008-02-28.
// Free to modify and redistribute with credit.

// EDIT: This plug-in has been modified from the original source to enable
// some additional functionality.
//
// a) We now return the newly created "truncated" elements as a jQuery
//    collection. This can be restored as usual using .end().
// b) We trigger the "expand.truncate" and "collapse.truncate" events when
//    the occur. The event object has an additional .relatedTarget property
//    which is the original expanded element.
// c) We add an "ellipses" option that places the ellipses outside of the
//    expand/collapse links.
//
// We do this because this is the best plug-in I've found that handles
// truncation of elements containing HTML components. Even better would be
// to find one that can also be provided with a number of lines.
//
// Requirements are:
//
// 1. Must truncate the contents of an element keeping elements intact.
// 2. Must be extensible trigger events when expand/collapse occurs.
// 3. Truncate to a set number of lines rather than just characters.
//
(function($) {

  var trailing_whitespace = true;

  $.fn.truncate = function(options) {

    var opts = $.extend({}, $.fn.truncate.defaults, options);

    var collected = this.map(function() {

      var content_length = $.trim(squeeze($(this).text())).length;
      if (content_length <= opts.max_length)
        return;  // bail early if not overlong
      
      // include more text, link prefix, and link suffix in max length
      var actual_max_length = opts.max_length - opts.more.length - opts.link_prefix.length - opts.link_suffix.length;

      var truncated_node = recursivelyTruncate(this, actual_max_length);
      var full_node = $(this).hide();

      truncated_node.insertAfter(full_node);

      findNodeForMore(truncated_node).append(opts.ellipses + opts.link_prefix+'<a href="#more" class="'+opts.css_more_class+'">'+opts.more+'</a>'+opts.link_suffix);
      findNodeForLess(full_node).append(opts.link_prefix+'<a href="#less" class="'+opts.css_less_class+'">'+opts.less+'</a>'+opts.link_suffix);

      truncated_node.find('a:last').click(function(event) {
        event.preventDefault();
        truncated_node.hide(); full_node.show();

        // Trigger an event for extensibility.
        truncated_node.trigger({
          type: 'expand.truncate',
          relatedTarget: full_node[0]
        });
      });
      full_node.find('a:last').click(function(event) {
        event.preventDefault();
        truncated_node.show(); full_node.hide();

        // Trigger an event for extensibility.
        truncated_node.trigger({
          type: 'collapse.truncate',
          relatedTarget: full_node[0]
        });
      });

      // Return our new truncated node.
      return truncated_node[0];
    });

    // Return the newly created elements.
    return this.pushStack(collected);
  }

  // Note that the " (…more)" bit counts towards the max length – so a max
  // length of 10 would truncate "1234567890" to "12 (…more)".
  $.fn.truncate.defaults = {
    max_length: 100,
    more: 'more',
    less: 'less',
    ellipses: '…',
    css_more_class: 'truncator-link truncator-more',
    css_less_class: 'truncator-link truncator-less',
    link_prefix: ' (',
    link_suffix: ')'
  };

  function recursivelyTruncate(node, max_length) {
    return (node.nodeType == 3) ? truncateText(node, max_length) : truncateNode(node, max_length);
  }

  function truncateNode(node, max_length) {
    var node = $(node);
    var new_node = node.clone().empty();
    var truncatedChild;
    node.contents().each(function() {
      var remaining_length = max_length - new_node.text().length;
      if (remaining_length == 0) return;  // breaks the loop
      truncatedChild = recursivelyTruncate(this, remaining_length);
      if (truncatedChild) new_node.append(truncatedChild);
    });
    return new_node;
  }

  function truncateText(node, max_length) {
    var text = squeeze(node.data);
    if (trailing_whitespace)  // remove initial whitespace if last text
      text = text.replace(/^ /, '');  // node had trailing whitespace.
    trailing_whitespace = !!text.match(/ $/);
    var text = text.slice(0, max_length);
    // Ensure HTML entities are encoded
    // http://debuggable.com/posts/encode-html-entities-with-jquery:480f4dd6-13cc-4ce9-8071-4710cbdd56cb
    text = $('<div/>').text(text).html();
    return text;
  }

  // Collapses a sequence of whitespace into a single space.
  function squeeze(string) {
    return string.replace(/\s+/g, ' ');
  }

  // Finds the last, innermost block-level element
  function findNodeForMore(node) {
    var $node = $(node);
    var last_child = $node.children(":last");
    if (!last_child) return node;
    var display = last_child.css('display');
    if (!display || display=='inline') return $node;
    return findNodeForMore(last_child);
  };

  // Finds the last child if it's a p; otherwise the parent
  function findNodeForLess(node) {
    var $node = $(node);
    var last_child = $node.children(":last");
    if (last_child && last_child.is('p')) return last_child;
    return node;
  };

})(jQuery);
