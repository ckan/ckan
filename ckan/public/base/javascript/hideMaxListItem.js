// HIDE MAX LIST ITEMS JQUERY PLUGIN
// Version: 1.34
// Author: www.joshuawinn.com
// Usage: Free and Open Source. WTFPL: http://sam.zoy.org/wtfpl/


function onPageLoad(facetName, title){  
     
    var moreText = 'Show More ' + title;
    var lessText = 'Show Only Popular ' + title;  
   
	jQuery('#' + facetName).hideMaxListItems({ 'max': 5,
												 'speed': 0,
												 'moreText': moreText,
												 'lessText': lessText,											 
												 'moreHTML': '<p class="maxlist-more module-footer" id="show-more-' + facetName + '"><a href="#" class="read-more" id="facet_read_more" name="sm_' + facetName + '"></a></p>'
											  });
  
    jQuery("#show-more-" + facetName).click(function(){				
						
			jQuery('ul[name="facet"]').each(function(){
				var id = $(this).attr('id');
				
				if(jQuery("#show-more-" + facetName).text().trim() === lessText) {	
				    
					$('#' + id).children("li").each(function() {
							
						var href = $(this).find('a').attr('href');
						if(href.indexOf('_' + facetName + '_limit=0') == -1)
							$(this).find('a').attr('href', href + '&_' + facetName + '_limit=0');
					});					             
				}
			
				if(jQuery("#show-more-" + facetName).text().trim() === moreText) {
					jQuery('#' + id).children("li").each(function() {			
						var href = $(this).find('a').attr('href')
						href = href.replace('&_' + facetName + '_limit=0', '');
						$(this).find('a').attr('href', href);
					});
								
				}
			});			           
	});
 }

				
(function($){

$.fn.extend({ 
hideMaxListItems: function(options) 
{     
	// DEFAULT VALUES
	var defaults = {
		max: 3,
		speed: 1000,
		moreText:'READ MORE',
		lessText:'READ LESS',
		moreHTML:'<p class="maxlist-more"><a href="#"></a></p>', // requires class and child <a>		
	};
	var options =  $.extend(defaults, options);
	
	// FOR EACH MATCHED ELEMENT
	return this.each(function() {
		var op = options;
		var totalListItems = $(this).children("li").length;
		var speedPerLI;
		
		// Get animation speed per LI; Divide the total speed by num of LIs. 
		// Avoid dividing by 0 and make it at least 1 for small numbers.
		if ( totalListItems > 0 && op.speed > 0  ) { 
			speedPerLI = Math.round( op.speed / totalListItems );
			if ( speedPerLI < 1 ) { speedPerLI = 1; }
		} else { 
			speedPerLI = 0; 
		}
		
		var browserUrl = window.location.href;
		var facetName = $(this).attr('id')
		// If list has more than the "max" option
		if ( (totalListItems > 0) && (totalListItems > op.max) )
		{
		    if(browserUrl.indexOf('_' + facetName + '_limit=0') == -1) {
		        //console.log();
		    	// Initial Page Load: Hide each LI element over the max
				$(this).children("li").each(function(index) {
					if ( (index+1) > op.max ) {
						$(this).hide(0);
						$(this).addClass('maxlist-hidden');
					}
			 	});
			}
			
			// Replace [COUNT] in "moreText" or "lessText" with number of items beyond max
			var howManyMore = totalListItems - op.max;
			var newMoreText = op.moreText;
			var newLessText = op.lessText;
			
			if (howManyMore > 0){
				newMoreText = newMoreText.replace("[COUNT]", howManyMore);
				newLessText = newLessText.replace("[COUNT]", howManyMore);
			}
			// Add "Read More" button			
			$(this).after(op.moreHTML);
			
			if(browserUrl.indexOf('_' + facetName + '_limit=0') == -1) {
				// Add "Read More" text
				$(this).next(".maxlist-more").children("a").text(newMoreText);			
			}
			else {
			    // Add "Read Less" text
				$(this).next(".maxlist-more").children("a").text(newLessText);			
			}
			// Click events on "Read More" button: Slide up and down
			$(this).next(".maxlist-more").children("a").click(function(e)
			{
				// Get array of children past the maximum option 
				var listElements = $(this).parent().prev("ul, ol").children("li"); 
				listElements = listElements.slice(op.max);
				
				// Sequentially slideToggle the list items
				// For more info on this awesome function: http://goo.gl/dW0nM
				if ( $(this).text() == newMoreText ){					
					$(this).text(newLessText);									
					var i = 0; 
					(function() { $(listElements[i++] || []).slideToggle(speedPerLI,arguments.callee); })();
				} 
				else {			
					$(this).text(newMoreText);
					var i = listElements.length - 1; 
					(function() { $(listElements[i--] || []).slideToggle(speedPerLI,arguments.callee); })();
				}
				
				// Prevent Default Click Behavior (Scrolling)
				e.preventDefault();
			});
		}
	});
}
});



$('[name="facet"]').each(function(){	
	facetName = $(this).attr('id');
    title = $.trim($('#sec-' + facetName).find('span').text());
	onPageLoad(facetName, title);
});

})(jQuery); // End jQuery Plugin

