(function () {
     'use strict';

     var user_role = document.querySelector('head').getAttribute('data-user-role');
     if (user_role && user_role == 'editor') {
        $('#field-private').parent().parent().hide();
     }

  })();