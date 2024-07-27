window.addEventListener('load', function(){
  $(document).ready(function(){
    let dtShowAll = $('a.dt-show-all');
    let dtHideAll = $('a.dt-hide-all');
    let dtColSelects = $('.dt-select-columns').find('input[type="checkbox"]').not('input[value="_id"]');
    $(dtShowAll).on('click', function(_event){
      $(dtColSelects).prop('checked', true).change().blur();
    });
    $(dtHideAll).on('click', function(_event){
      $(dtColSelects).prop('checked', false).change().blur();
    });
  });
});
