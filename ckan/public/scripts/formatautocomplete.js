(function($){
    var url = "";

    function extractDataAttributes(){
        var el = $(this);
        $.each(this.attributes, function(){
            // get the autocomplete API URL
            if(this.name === 'data-format-autocomplete-url'){
                url = this.value;
            }
        });
    }

    function autoCompleteList(request, response){
        var requestData = {'incomplete': request.term};

        $.ajax({
            url: url,
            data: requestData,
            dataType: 'jsonp',
            type: 'get',
            jsonpCallback: 'callback',
            success: function(json){
                var formats = [];
                $.each(json["ResultSet"]["Result"], function(){
                    formats.push(this["Format"]);
                });
                response(formats);
            },
        });
    }

    $(document).ready(function(){
        $('.format-autocomplete').focus(extractDataAttributes)
            .autocomplete({source: autoCompleteList});
    });
})(jQuery);
