/** Tracking JS Module
 *
 * This simple module will be loaded on each page and will send POST
 * requests to the server to track the current page view and any
 * resource link containing the class 'resource-url-analytics'.
 *
 * Page view will contain the parameter 'type' set to 'page' and
 * resource link will contain the parameter 'type' set to 'resource'.
 *
 * Note: CKAN core already contains some links with resource-url-analytics
 * class. You can add resource-url-analytics class to any link in your
 * templates to also track it.
 *
*/
$(function (){
    // remove any site root from url and trim any trailing /
    var url = location.pathname;
    url = url.substring($('body').data('locale-root'), url.length);
    url = url.replace(/\/*$/, '');

    // POST request for each visited page
    $.ajax({url : $('body').data('site-root') + '_tracking',
            type : 'POST',
            data : {url:url, type:'page'},
            timeout : 300 });

    // POST request when clicking links with class 'resource-url-analytics'
    $('a.resource-url-analytics').on('click', function (e){
      var url = $(e.target).closest('a').attr('href');
      $.ajax({url : $('body').data('site-root') + '_tracking',
              data : {url:url, type:'resource'},
              type : 'POST',
              timeout : 30});
    });
  });
