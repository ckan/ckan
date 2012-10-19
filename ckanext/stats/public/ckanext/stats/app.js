jQuery(document).ready(function($) {
	$('form').submit(function(e) {
		e.preventDefault();
		attribute = $('#form-attribute').val();
		loadSolr(attribute);
	})
	// default! (also in html)
	loadSolr('tags');

	function loadSolr(attribute) {
		var url = solrCoreUrl + '/select?indent=on&wt=json&facet=true&rows=0&indent=true&facet.mincount=1&facet.limit=30&q=*:*&facet.field=' + attribute;
		function handleSolr(data) {
			var results = [];
			ourdata = data.facet_counts.facet_fields[attribute];
			var newrow = {};
			for (ii in ourdata) {
				if (ii % 2 == 0) {
					newrow.name = ourdata[ii];
					if (!newrow.name) {
						newrow.name = '[Not Specified]';
					}
				} else {
					newrow.count = ourdata[ii];
					results.push(newrow);
					newrow = {};
				}
			}
			display(results);
		}

		$.ajax({
			url: url,
			success: handleSolr,
			dataType: 'jsonp',
			jsonp: 'json.wrf'
		});
	}

	function display(results) {
		var list = $('#category-counts');
		list.html('');
		if (results.length == 0) {
			return
		}
		var maximum = results[0]['count'];
		for(ii in results) {
			maximum = Math.max(maximum, results[ii]['count']);
		}

		$.each(results, function(idx, row) {
			var newentry = $('<li></li>');
			newentry.append($('<a href="#">' + row['name'] + '</a>'));
			newentry.append($('<span class="count">' + row['count'] + '</a>'));
			var percent = 100 * row['count'] / maximum;
			newentry.append($('<span class="index" style="width: ' + percent + '%"></span>'));
			list.append(newentry);
		});
	}
});
