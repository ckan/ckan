$(document).ready(function() {
    var getProxyJSON = function(host, path, data, callback) {
        data['host'] = host;
        data['path'] = path;
        var uri = TRACEBACK.uri+'/relay';
        $.getJSON(uri, data, callback);
    };
    
    // Manipulate DOM to add the iframe, and move things around
    var newholder = $(document.createElement("div")).addClass('widget_layout');
    $('div.feature-highlight').wrapAll(newholder[0])[0].appendChild(
        $('button:last').remove()[0]);
    $('div.widget_layout')[0].appendChild(document.getElementById('service_widget'));
        
    $('#service_widget input.submit_traceback').click(function () {
        $('#service_widget .posttracebacktab').html('Sending traceback...');
        var uri = TRACEBACK.uri+'/post_traceback?debugcount='+debug_count
            +'&host='+encodeURIComponent(TRACEBACK.host)
            +'&path='+encodeURIComponent(TRACEBACK.traceback);
        var opts = {
            url: uri,
            cache: false,
            dataType: 'json',
            success: function(data, textStatus) {
                var iframe = document.createElement("iframe");
                var tlink = data.traceback.link.replace(/\.xml/, '');
                iframe.style.display = "none";
                document.body.appendChild(iframe);
                iframe.src = 'http://'+TRACEBACK.host+TRACEBACK.traceback
                    +'/'+encodeURIComponent(tlink)
                    +'/reown?uuid='+encodeURIComponent(data.traceback.uuid);
                stuff = data;
                var full_uri = 'http://' + TRACEBACK.host + TRACEBACK.traceback + '/' + tlink;
                var reply = '<b>Traceback posted successfully</b>.<br /><br />';
                reply += ' <a href="' + full_uri;
                reply += '">' + full_uri + '</a>';
                $('#service_widget .posttracebacktab').html(reply);
            }
        };
        $.ajax(opts);
        return false;
    });
    
    // Hide the tabs we shouldn't see
    $('.posttracebacktab, .searchtab').hide();
    
    // Bind the click functions for each tab
    $('a.overview').click(function () {
        $('#supportnav li').removeClass('active');
        $(this).parent().addClass('active');
        $('.overviewtab').show();
        $('.posttracebacktab, .searchtab').hide();
        return false;
    });
    
    $('a.search').click(function () {
        $('#supportnav li').removeClass('active');
        $(this).parent().addClass('active');
        $('.searchtab').show();
        $('.posttracebacktab, .overviewtab').hide();
        return false;
    });
    
    $('a.posttraceback').click(function () {
        $('#supportnav li').removeClass('active');
        $(this).parent().addClass('active');
        $('div.posttracebacktab').show();
        $('.searchtab, .overviewtab').hide();
        return false;
    });
    
    // Set the search field to the exception as the default search
    $('.searchtab input[@type="text"]')[0].value = $('code.main-exception').text();
    
    // Bind the search button to hit the mail lists
    $('.searchtab input[@type="submit"]').click(function () {
        
        // Populate the lists array with the strings for the lists to include
        // in the search
        var lists = [];
        var options = $('.searchtab input[@type="checkbox"]').serializeArray();
        $.each(options, function(i, val) {
            lists.push('list:' + val.value);
        });
        
        // Setup the search data
        var data = {mode:'json', page:1};
        data.q = lists.join(' ') + " " + $('.searchtab input[@type="text"]')[0].value;
        
        var sr = $('.searchresults');
        sr.html('Loading...');
        var searchResults = getProxyJSON('markmail.org', '/results.xqy', data,
            function(data, textStatus) {
                stuff = data;
                var numresults = $(document.createElement('p'));
                numresults.addClass('results');
                numresults.html(data.search.start + ' to ' + data.search.end 
                    + ' of ' + data.search.estimation);
                var searchlink = document.createElement('a');
                searchlink.href = 'http://markmail.org' + data.search.permalink;
                searchlink.target = '_blank';
                $(searchlink).html('View all results');
                numresults.prepend(searchlink);
                sr.html('').append(numresults);
                
                // If there's no search results, stop here
                if (!data.search.results) {
                    return false;
                }
                
                // Iterate through the search results adding them dynamically
                // to the element
                $.each(data.search.results.result, function(i, val) {
                    var result = $(document.createElement('div')).addClass('result');
                    var link = document.createElement('a');
                    link.href = 'http://markmail.org' + val.url;
                    link.target = '_blank';
                    $(link).html(val.subject);
                    result.append(link);
                    var blurb = $(document.createElement('div')).addClass('blurb');
                    blurb.html(val.blurb);
                    result.append(blurb);
                    var meta = $(document.createElement('div')).addClass('meta');
                    meta.html(val.date + ' - ' + val.from + ' - ' + val.list);
                    result.append(meta);
                    sr.append(result);
                });
                
                // Scroll the window down to the top of the service widget with some space
                window.scrollTo(0, $('#service_widget').offset().top-20);
            });
        return false;
    });
});
