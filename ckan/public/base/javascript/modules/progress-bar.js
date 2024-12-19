this.ckan.module('progress-bar', function ($) {
  return {
    options: {
      endpoint: '',
      percentage: false,
    },

    initialize: function () {
      let options = this.options;
      let el = this.el;

      if( options.endpoint.length > 0 ){

        $(el).append('<div class="progress"><div class="progress-bar" role="progressbar" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100"></div></div><small class="progress-bar-label"></small>');
        let progressBarWrapper = $(el).find('.progress');
        let progressBar = $(el).find('.progress-bar');
        let progressBarLabel = $(el).find('.progress-bar-label');

        function update_bar(_total, _current, _state, _label, _timestamp){
          let label = '';
          if( _label.length > 0 ){
            label = _label;
            if( _timestamp.length > 0 ){
              label += ' (' + _timestamp + ')';
            }
          }else if( _timestamp.length > 0 ){
            label = _timestamp;
          }
          if( label.length > 0 ){
            $(progressBarLabel).text(label);
          }
          $(progressBarWrapper).attr('data-state', _state);
          if( ! _total || ! _current ){
            return
          }
          let val = (_current / _total) * 100;
          if( _total != _current ){
            $(progressBar).animate({'width': val + '%'}, 635);
          }else{
            $(progressBar).css({'width': val + '%'});
          }
          if( options.percentage != false ){
            $(progressBar).text(val + '%');
            $(progressBar).attr('aria-valuenow', val);
          }else{
            $(progressBar).text(_current + '/' + _total);
            $(progressBar).attr('aria-valuemax', _total);
            $(progressBar).attr('aria-valuenow', _current);
          }
        }

        function heartbeat(){
          $.ajax({
            'url': options.endpoint,
            'type': 'GET',
            'dataType': 'JSON',
            'complete': function(_data){
              if( _data.responseJSON ){  // we have response JSON
                // label should be optional
                _label = '';
                if( typeof _data.responseJSON.label != 'undefined' ){
                  _label = _data.responseJSON.label
                }
                // last updated should be optional
                _timestamp = '';
                if( typeof _data.responseJSON.last_updated != 'undefined' ){
                  _timestamp = _data.responseJSON.last_updated
                }
                update_bar(_data.responseJSON.total,
                           _data.responseJSON.current,
                           _data.responseJSON.state,
                           _label,
                           _timestamp);
                if( _data.responseJSON.state == 'complete' || _data.responseJSON.state == 'error' ){
                  return
                }
                if( _data.responseJSON.total == _data.responseJSON.current){
                  return
                }
                setTimeout(heartbeat, 5000);
              }else{  // fully flopped ajax request
                // just try again...
                setTimeout(heartbeat, 5000);
              }
            }
          });
        }

        heartbeat();

      }
    }
  };
});
