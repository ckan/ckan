(function( $ ) {

 //sortList function
 $.fn.sortList = function(sort, sortType) {
    
    //cnt = $(this).children('li:not(.maxlist-hidden)').get().length;
    cnt = $(this).children('li:visible').get().length;
    var mylist = $(this);
    var listitems = $('li', mylist).get();
    
    if(sort == 'desc') {
        //descending sort
    	if(sortType  == 'alphaSort') {
            mylist.removeClass('alph_asc');
            mylist.removeClass('cnt_asc');
            mylist.removeClass('cnt_desc');
            mylist.addClass('alph_desc');
        }
        else {
            mylist.removeClass('alph_asc');
            mylist.removeClass('cnt_asc');
            mylist.removeClass('alph_desc');
            mylist.addClass('cnt_desc');
        }
    }   
    else {
        //ascending sort
        if(sortType  == 'alphaSort') {
            mylist.removeClass('alph_desc');
            mylist.removeClass('cnt_asc');
            mylist.removeClass('cnt_desc');
            mylist.addClass('alph_asc');
        }
        else {
            mylist.removeClass('cnt_desc');
            mylist.removeClass('alph_desc');
            mylist.removeClass('alph_asc');
            mylist.addClass('cnt_asc');
        }
    }
    
    if(listitems.length > 1) {
         
	    listitems.sort(function(a, b) {
    
    	    if(sortType == 'alphaSort') {
        		var compA = $.trim($(a).text().toUpperCase());
        		var compB = $.trim($(b).text().toUpperCase()); 
        	}
        	else { 
            	var compA_arr = $(a).text().split("(");
            	var compB_arr = $(b).text().split("(");
            	var compA = parseInt($.trim(compA_arr[compA_arr.length-1].split(')')[0]));
            	var compB = parseInt($.trim(compB_arr[compB_arr.length-1].split(')')[0]));
        	}
        
        	if(sort == 'asc') 
        		return (compA < compB) ? -1 : 1;
         	else
        		return (compA > compB) ? -1 : 1;  
        
    	});//end of listitems sort
    }//end of if
    
    //add sorted list to ul
    $.each(listitems, function(i, itm) {
    	if(cnt > 0) {
           $(itm).removeClass('maxlist-hidden');
           $(itm).removeAttr('style');
        }
        else if(!$(itm).hasClass('maxlist-hidden')) {
             $(itm).addClass('maxlist-hidden');
             $(itm).css('display', 'none');
    	}
        mylist.append(itm);
        cnt--;
    }); //end of each fn
    
    var id = $(this).attr('id');

    imageChange(sortType, id, sort);
    	

    
 }//end of sort function
 
 
 function changeURL(id, sort, sortType) {
 
 	$('[name="facet"] a').each(function(){

   		var url = $(this).attr('href');
   		url = url.replace('&_' + id  + '_sortAlpha=desc', '');
   		url = url.replace('&_' + id  + '_sortAlpha=asc', '');
   		url = url.replace('&_' + id  + '_sortCnt=desc', '');
   		url = url.replace('&_' + id  + '_sortCnt=asc', '');
   		
   		if(sortType == 'alphaSort') {
   		    
   		    if(sort == 'desc')
   		       url = url + '&_' + id  + '_sortAlpha=desc';
   		     else
   		       url = url + '&_' + id  + '_sortAlpha=asc';
   		}
   		else {
   
   		    if(sort == 'desc')
   		       url = url + '&_' + id  + '_sortCnt=desc';
   		     else
   		       url = url + '&_' + id  + '_sortCnt=asc';
   		}
   		
   		$(this).attr('href', url);
 	});
 }
 
 
 function imageChange(sortType, key, sort) {

        if(sortType == 'alphaSort') {

            $('#' + key).parent().parent().find('img#sortFacetCount').attr('src', '/base/images/number.png')

            if(sort == 'desc')
                $('#' + key).parent().parent().find('img#sortFacetAlpha').attr('src', '/base/images/alpha_down.png');
            else
                $('#' + key).parent().parent().find('img#sortFacetAlpha').attr('src', '/base/images/alpha_up.png');

        }

        if(sortType == 'cntSort') {

            $('#' + key).parent().parent().find('img#sortFacetAlpha').attr('src', '/base/images/alpha.png');

            if(sort == 'desc')
                $('#' + key).parent().parent().find('img#sortFacetCount').attr('src', '/base/images/number_down.png');
            else
                $('#' + key).parent().parent().find('img#sortFacetCount').attr('src', '/base/images/number_up.png');
        }

 }
 
 $.extend({
        getUrlVars: function(){
            var vars = [], hash;
            var hashes = window.location.href.slice(window.location.href.indexOf('?') + 1).split('&');
            for(var i = 0; i < hashes.length; i++) {
                hash = hashes[i].split('=');
                vars.push(hash[0]);
                vars[hash[0]] = hash[1];
            }
            return vars;
        },

        getUrlVar: function(name){
            return $.getUrlVars()[name];
        }
 });
 
 /**
  * for all Show more/show less links modify link to take you to that facet
 **/
 $('a#facet_read_more').each( function() {
        var name = $(this).attr('name').split("sm_")[1];
        var url = $(this).attr('href');

        if(url.indexOf('#sec-' + name) == -1)
            url = url.replace('#', '') + '#sec-' + name;
            
        $(this).click(function(){ 
           location.href = url;
        });    
            
    });
   
 /**
  * for Alphabatical sort set param 'sortType' to alphaSort
  * for Count sort set param 'sortType' to cntSort
  * for sort order set param 'sort' to asc or desc
 **/
 var defaults = {
      'metadata_type' : {'sortType': 'cntSort', 'sort' : 'desc'},
      'tags' : {'sortType': 'cntSort', 'sort' : 'desc'},
      'res_format' : {'sortType': 'cntSort', 'sort' : 'desc'},
      'groups' : {'sortType': 'cntSort', 'sort' : 'desc'},
      'organization_type' : {'sortType': 'cntSort', 'sort' : 'desc'},
      'organization' : {'sortType': 'cntSort', 'sort' : 'desc'},
      'vocab_category_all' : {'sortType': 'cntSort', 'sort' : 'desc'},
      'dataset_type' : {'sortType': 'cntSort', 'sort' : 'desc'},
      'harvest_source_title' : {'sortType': 'cntSort', 'sort' : 'desc'},
      'frequency' : {'sortType': 'cntSort', 'sort' : 'desc'},
      'source_type' : {'sortType': 'cntSort', 'sort' : 'desc'},
      'publisher' : {'sortType': 'cntSort', 'sort' : 'desc'}
 };
 
 var allVars = $.getUrlVars();
 var paramArr=[];
 var defaultArr = defaults;

 if(allVars[0] != window.location.href) {

    for(var i = 0; i < allVars.length; i++) {
         
        var sort = $.getUrlVar(allVars[i]).split('#')[0];
         
    	if(sort == 'asc' || sort == 'desc') {
    	     var id, sortType;
                var parts = allVars[i].split('_');

                if(parts[parts.length-1] == 'sortAlpha')
                    sortType = 'alphaSort';
                else
                    sortType = 'cntSort';

                if(parts.length > 3) {
                    parts.splice(0,1);
                    parts.splice(parts.length-1, 1);

                    id = parts.join('_');
                }
                else
                    id = parts[1];

                paramArr.push(id);
                
                $('ul#' + id).sortList(sort, sortType);
    	}//end of if
    
    }//end of for
    
    var diff = {};
    $.each(defaults, function(i,e) {
       if ($.inArray(i, paramArr) == -1) {
           diff['' + i + ''] = e;
        }
    });

    defaultArr = diff;
        
 }//end of if

 $.each(defaultArr, function(i,e) {
 
    if($('ul#'+ i).length > 0) 
       $('ul#' + i).sortList(e['sort'], e['sortType']);   
    
 });
 
 $("img#sortFacetAlpha").click(function() {
  	
  	 var id = $(this).parent().parent().find('ul.unstyled.nav.nav-simple.nav-facet').attr('id');
  	 var mylist = $('ul#' + id);
  	
  	 if(mylist.hasClass('alph_asc')) 
         var sort = 'desc';
  	 else
  	     var sort = 'asc';
  	 
  	 mylist.sortList(sort, 'alphaSort');
  	 
  	 changeURL(id, sort, 'alphaSort');
  	
 }); //end of img#sortFacetAlpha
  
 $("img#sortFacetCount").click(function() {
  
     var id = $(this).parent().parent().find('ul.unstyled.nav.nav-simple.nav-facet').attr('id');
  	 var mylist = $('ul#' + id);
  	
  	 if(mylist.hasClass('cnt_asc')) 
         var sort = 'desc';
  	 else
  	     var sort = 'asc';
  	 
  	 mylist.sortList(sort, 'cntSort');
  	 changeURL(id, sort, 'cntSort');
  
 }); //end of img#sortFacetCount  

})( jQuery );
