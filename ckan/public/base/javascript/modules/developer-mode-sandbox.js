/* Loads the API Info snippet into a modal dialog. Retrieves the snippet
 * url from the data-snippet-url on the module element.
 *
 * template - The url to the template to display in a modal.
 *
 * Examples
 *
 *   <a data-module="api-info" data-module-template="http://example.com/path/to/template">API</a>
 *
 */
 "use strict";
 this.ckan.module('developer-mode-sandbox', function (jQuery, _) {
  return {

    options: {


    },

    // in_progres flag
    inProgress: false,

    // base url to ckan api
    actionsUrl: 'api/3/action/',

    // select field with all actions
    selector: null,

    // sandbox switcher
    sandboxer: null,

    //enable sandbox
    isSandbox: false,

    // form container with API forms
    formContainer: null,

    // placeholder not_chosen
    notChosenContainer: null,

    // container for request results
    resultContainer: null,

    // container for request examples
    examplesContainer: null,

    // is placeholder not_chosen shown?
    notChosen: true,

    // investigated action
    currentAction: null,

    // input markdown
    input:
    '<div class="control-group ">' +
    '<label class="control-label" for="sandbox-generated-{{name}}">{{label}}</label>' +
    '<div class="controls ">' +
    '<input id="sandbox-generated-{{name}}" type="text" name="{{name}}" value="" placeholder="{{label}}">' +
    '</div>' +
    '</div>',

    submit:
    '<div class="form-actions"><button class="btn btn-primary" type="submit" name="save"><i class="icon-play-circle"></i></button></div>',

    // regexp to search params
    getParams: function(data){
      var result = [];
      var regexp = /(?::param\s*)(\w*?):/g;

      var match = null;

      while ((match = regexp.exec(data)) != null) {
        result.push(match[1]);
      }

      return result;
    },

    generateUrl: function (action) {
      return this.sandbox.client.url(this.actionsUrl + action);
    },

    /* Initialize page.
     *
     * Returns nothing.
     */
     initialize: function () {
      jQuery.proxyAll(this, /_on/);

      // find select with actions and add EventListener
      this.selector = this.el.find('#field-action-selector');
      this.selector.on('change', this._onSelectAction);

      // find select with actions and add EventListener
      this.sandboxer = this.el.find('#checkbox-is-sandbox');
      this.sandboxer.on('change', this._onSwitchSandbox);

      // find container for our future forms
      this.formContainer = this.el.find('#action-form');
      this.formContainer.on('submit', this._onSubmitAction);

      // find container for not_chosen and request errors
      this.notChosenContainer = this.el.find('.not-chosen-action');

      // find container for examples
      this.examplesContainer = this.el.find('#request-code');

      // find container for not_chosen and request errors
      this.resultContainer = this.el.find('#request-result');

      // make blank default value that doesn't appear in options
      this.selector.prop('selectedIndex', -1);

      // find conteiner for help text
      this.helpArea = this.el.find('#action-help');

    },

    /* Turn on/off sandbox mode
     *
     * Returns nothing
     */
    _onSwitchSandbox: function (event) {
      if (this.sandboxer.prop('checked'))
        this.isSandbox = true;
      else
        this.isSandbox = false;
    },

    /* After change of select value.
     *
     * Returns nothing.
     */
     _onSelectAction: function (event) {
      // only single request at time
      if (this.inProgress)
        return;

      // request_in_progress flag
      this.selector.attr('disabled', true);
      this.inProgress = true;

      this.helpArea.text('');
      this.formContainer.text('');
      this.resultContainer.text('');
      this.examplesContainer.text('');

      // hide hot_chosen placeholder
      if (this.notChosen){
        this.notChosenContainer.hide();
        this.notChosen = false;
      }

      // change investigated action
      this.currentAction = this.selector.val();

      // generate url to receive help text
      var help_url = this.generateUrl('help_show');

      // make request's body
      var request = $.get( help_url, {name: this.currentAction});

      // Event listeners for success, error and any result
      request.done(this._onReceiveHelp);
      request.fail(this._onFailHelp);
      request.always(this._onHelpFinished);
    },

    /* After success help request.
     * Change text area content and generate form.
     *
     * Returns nothing.
     */
     _onReceiveHelp: function(data){
      var content = data.result;
      // put description in helpArea
      this.helpArea.text(content.trim());

      // parse all available params
      var params = this.getParams(content);
      var len = params.length;

      // add field for each param
      for(var i = 0; i < len; i++){
        var input = this.input.replace(/{{label}}|{{name}}/g, params[i]);
        this.formContainer.append(input);
      }

      // add submit button
      this.formContainer.append(this.submit);

    },

    /* After failed help request.
     * Clear helpArea and forms. Show error.
     *
     * Returns nothing.
     */
     _onFailHelp: function (data, status, msg) {
      this.notChosenContainer.text(status + ': ' + msg).show();
      this.notChosen = true;
    },

    /* After any help request.
     * Enable action selector.
     *
     * Returns nothing.
     */
     _onHelpFinished: function (data, status, msg) {
      this.selector.attr('disabled', false);
      this.inProgress = false;
    },

    /* Instead of action submit.
     *
     * Returns nothing.
     */
     _onSubmitAction: function (event) {
      //
      if (this.inProgress)
        return;

      // generate url for API request
      var url = this.generateUrl(this.currentAction);

      var fields = this.formContainer.find('[type=text]');
      var len = fields.length;
      var data = {};

      for (var i = 0; i < len; i++){
        var val = fields[i].value;
        if (val)
          data[fields[i].name] = val;
      }

      if (this.isSandbox)
        data['sandbox'] = true;
      // request_in_progress flag
      this.selector.attr('disabled', true);
      this.inProgress = true;

      // in case of POST
      data = JSON.stringify(data);

      // let's show how this can be done
      this._onGenerateExamples(url, data);

      // make request's body
      console.log(data)
      var request = $.post(url, data, 'json');

      // // Event listeners for success, error and any result
      request.done(this._onActionDone);
      request.fail(this._onActionFail);
      request.always(this._onActionAfter);

      event.preventDefault();
      return false;
    },

    /* Make examples of requests
     *
     * Returns nothing.
     */
     _onGenerateExamples: function (url, data) {
      var examples = [];
      var commands = {};

      commands['CURL:'] = "curl " +
      url +
      " -H 'Authorization: API_KEY' -d '" +
      data +
      "'";

      commands['JavaScript:'] =
      "var api_key = API_KEY;\n" +
      "var data = " +
      JSON.stringify(JSON.parse(data), null, '\t') +
      ";\n" +
      "$.ajax({\n" +
        "\turl: '" +
        url +
        "',\n" +
        "\tdata: JSON.stringify(data),\n" +

        "\tbeforeSend: function (request){\n" +
            "\t\trequest.setRequestHeader('Authorization', api_key);\n" +
        "\t},\n" +

        "\tmethod: 'POST',\n" +
        "\tdataType: 'jsonp',\n" +
        "\tsuccess: function(data) {\n" +
        "\t\talert('Request status: ' + data.success);\n" +
        "\t}\n" +
        "});\n" ;

      for (command in commands){
        examples.push(
          $('<div>').append(
            $('<hr>'),
            $('<h3>').text(command),
            $('<p>').text(commands[command])
            )
          );
      }

      this.examplesContainer.empty().append(examples)
      },

    // after success API request
    _onActionDone: function (data, status, msg) {
      this.resultContainer.text(this.niceOutput(data.result));
    },

    // after wrong api request
    _onActionFail: function (data, status, msg) {
      var resp = typeof data.responseJSON === 'string' ?
      data.responseText :
      this.niceOutput(JSON.parse(data.responseText));
      this.resultContainer.text(resp);
    },

    // after any api request
    _onActionAfter: function (data, status, msg) {
      // here we are using small hack to escape html and save newlines&indents
      this.resultContainer.html(this.resultContainer.html()
        .replace((new RegExp('\\n','gm')), '</br>')
        .replace(new RegExp('\\t','gm'), '&emsp;&emsp;'));
      this._onHelpFinished(data, status, msg);
    },

    /* Stringify JSON. We could use JSON.stringify with secont param as well
     *
     * Returns object as string.
     */
     niceOutput: function (value) {
      var result = '{\n';

      // recursion to show nested objects
      (function prettyfier(obj, repeat){
        var indent = '\t'.repeat(repeat);
        for (var key in obj){
          var item = obj[key];
          if ( item === null){
            result += indent + key + ': null\n';
          } else if (typeof item === 'object'){
            result += indent + key + ': {\n';
            prettyfier(item, repeat+1);
            result += indent + '}\n'
          } else {
            result += indent + key + ': ' + item + '\n';
          }

        }
      }(value, 1));
      result += '}';
      return result;
    },

  };
});
