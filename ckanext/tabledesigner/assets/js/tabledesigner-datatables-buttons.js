/**
 * Adds table designer buttons to the datatable view.
 */
this.ckan.module('tabledesigner_datatables_buttons', function ($, _) {
  return {
    options: {
      type: null,
      text: null,
      url: null,
      buttonClass: 'btn-tabledesigner',
    },
    initialize: function () {
      if (!this.options.type || !this.options.text || !this.options.url) {
        console.error('tabledesigner_datatables_buttons: Missing required options');
        return;
      }

      const buttonType = this.options.type;
      const text = this.options.text;
      const url = this.options.url;
      const buttonClass = this.options.buttonClass;
      function _addButton(settings, json) {
        const table = $(settings.nTable).DataTable();
        let buttonConfig = { text: text, className: buttonClass };

        switch (buttonType) {
          case 'add':
            buttonConfig.action = () => window.parent.location = url;
            break;
          case 'edit':
            buttonConfig.extend = "selectedSingle";
            buttonConfig.action = function (e, dt, button, config) {
              var _id = dt.rows({ selected: true }).data()[0]._id;
              window.parent.location = url + '?_id=' + encodeURIComponent(_id);
            };
            break;
          case 'delete':
            buttonConfig.extend = "selected";
            buttonConfig.action = function (e, dt, button, config) {
              var _ids = dt.rows({ selected: true }).data().map(
                e => encodeURIComponent(e._id)).join('&_id=');
              window.parent.location = url + '?_id=' + _ids;
            };
            break;
        }

        table.button().add(0, buttonConfig);
      }

      this.sandbox.subscribe("datatablesview:init-complete", _addButton);
    }
  }
});
