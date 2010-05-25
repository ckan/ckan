(function ($) {

  function extractDataAttributes() {
    var el = $(this);
    $.each(this.attributes, function () {
      var m = this.name.match(/data\-(\S+)/);
      if (m) { el.data(m[1], this.value); }
    });
  }

  function updateTagList(container, json) {
    $(container).empty();
    $.each(json["ResultSet"]["Result"], function () {
      $(container).append('<a>' + this["Name"] + '</a>');
    });
    $(container).children().first().addClass('active')
                .end().hover(function () {
                  $(this).addClass('active').siblings().removeClass('active');
                });
  }

  function checkForIncompleteTag() {
    var reqData = {},
        tagStr = $(this).val(),
        tagsContainer = $(this).next('.tags');

    // If we're not in the middle of typing a tag, return.
    if (tagStr[tagStr.length - 1] === ' ') {
      return;
    }
    
    var tags = tagStr.split(/\s+/),
    incomplete = tags[tags.length - 1];

    reqData[$(this).data('tagcomplete-queryparam')] = incomplete;
    
    var url = $(this).data('tagcomplete-url'),
        cbk = $(this).data('tagcomplete-callback');
    
    if (cbk) { url += '?' + cbk + '=?'; }
    
    $.getJSON(url, reqData, function (json) {
      updateTagList(tagsContainer, json);
    });
  }
  
  function maybeDoComplete(e) {
    var tagList = $(this).next('.tags'),
        tag = tagList.find('a.active');

    // Complete tag on {tab, return, right-arrow}.
    if (tag[0] && ($.inArray(e.keyCode, [9, 13, 39]) !== -1)) {
      var tags = $(this).val().split(/\s+/).slice(0, -1);
      tags.push(tag.text());
      $(this).val(tags.join(" ") + " ");
      tagList.empty();
      return false;
    }
  }

  $(document).ready(function () {
    $('.tagComplete').after('<div class="tags small"></div>')
                     .focus(extractDataAttributes)
                     .keydown(maybeDoComplete)
                     .keyup(checkForIncompleteTag);
  });
})(jQuery);
