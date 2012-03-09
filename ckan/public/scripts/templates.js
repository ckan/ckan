
CKAN.Templates.resourceAddLinkFile = ' \
  <form> \
    <dl> \
      <dt> \
        <label class="field_opt" for="url"> \
          '+CKAN.Strings.fileUrl+' \
        </label> \
      </dt> \
      <dd> \
        <input name="url" type="text" placeholder="http://mydataset.com/file.csv" style="width: 60%"/> \
        <input name="save" type="submit" class="pretty-button primary" value="'+CKAN.Strings.add+'" /> \
        <input name="reset" type="reset" class="pretty-button" value="'+CKAN.Strings.cancel+'" /> \
      </dd> \
    </dl> \
     \
  </form> \
';

CKAN.Templates.resourceAddLinkApi = ' \
  <form> \
    <dl> \
      <dt> \
        <label class="field_opt" for="url"> \
          '+CKAN.Strings.apiUrl+' \
        </label> \
      </dt> \
      <dd> \
        <input name="url" type="text" placeholder="http://mydataset.com/api/" style="width: 60%" /> \
        <input name="save" type="submit" class="pretty-button primary" value="'+CKAN.Strings.add+'" /> \
        <input name="reset" type="reset" class="pretty-button" value="'+CKAN.Strings.cancel+'" /> \
      </dd> \
    </dl> \
     \
  </form> \
';

CKAN.Templates.resourceUpload = ' \
<div class="fileupload"> \
  <form action="http://test-ckan-net-storage.commondatastorage.googleapis.com/" class="resource-upload" \
    enctype="multipart/form-data" \
    method="POST"> \
 \
    <div class="hidden-inputs"></div> \
    <dl> \
      <dt> \
        <label class="field_opt fileinput-button" for="file"> \
          '+CKAN.Strings.file+' \
        </label> \
      </dt> \
      <dd> \
        <input type="file" name="file" /> \
        <br /> \
        <div class="fileinfo"></div> \
        <input id="upload" name="upload" type="submit" class="pretty-button primary" value="'+CKAN.Strings.add+'" /> \
        <input id="reset" name="reset" type="reset" class="pretty-button" value="'+CKAN.Strings.cancel+'" /> \
      </dd> \
    </dl> \
  </form> \
  <div class="alert alert-block" style="display: none;"></div> \
  </div> \
</div> \
';



CKAN.Templates.resourceEntry = ' \
  <li class="ui-state-default resource-edit"> \
    <a class="resource-open-my-panel" href="#">\
      <div class="drag-bars">|||</div> \
      <img class="js-resource-icon inline-icon resource-icon" src="${resource_icon}" /> \
      <span class="js-resource-edit-name">${resource.name}</span>\
    </a>\
  </li>';

CKAN.Templates.resourceDetails = ' \
  <div style="display: none;" class="resource-details"> \
    <div class="flash-messages"> \
      <div class="error resource-errors"></div> \
    </div> \
    <table> \
      <tbody> \
        <tr> \
          <td class="dataset-label" property="rdfs:label">'+CKAN.Strings.name+'</td> \
          <td class="dataset-details" property="rdf:value"> \
            <input class="js-resource-edit-name" name="resources__${num}__name" type="text" value="${resource.name}" class="long" /> \
          </td> \
        </tr> \
        <tr> \
          <td class="dataset-label" property="rdfs:label">'+CKAN.Strings.description+'</td> \
          <td class="dataset-details" property="rdf:value"> \
            <div class="markdown-editor"> \
              <ul class="button-row"> \
                <li><button class="pretty-button js-markdown-edit depressed">Edit</button></li> \
                <li><button class="pretty-button js-markdown-preview">Preview</button></li> \
              </ul> \
              <textarea class="js-resource-edit-description markdown-input" name="resources__${num}__description">${resource.description}</textarea> \
              <div class="markdown-preview" style="display: none;"></div> \
              <span class="hints">You can use <a href="http://daringfireball.net/projects/markdown/syntax" target="_blank">Markdown formatting</a> here.</span> \
            </div> \
          </td> \
        </tr> \
        <tr> \
          <td title="${resource.url_error}" property="rdfs:label" class="dataset-label resource-edit-label{{if resource.url_error}} field_warning{{/if}}">'+CKAN.Strings.url+'</td> \
          <td class="dataset-details" property="rdf:value"> \
          {{if resource.resource_type=="file.upload"}} \
            ${resource.url} \
            <input name="resources__${num}__url" type="hidden" value="${resource.url}" /> \
          {{/if}} \
          {{if resource.resource_type!="file.upload"}} \
            <input name="resources__${num}__url" type="text" value="${resource.url}" class="long" title="${resource.url_error}" /> \
          {{/if}} \
          </td> \
        </tr> \
        </tr><tr> \
          <td class="dataset-label" property="rdfs:label">'+CKAN.Strings.format +'\
          &nbsp;&nbsp;<img class="js-resource-icon inline-icon resource-icon" src="${resource_icon}" /> \
          </td> \
          <td class="dataset-details" property="rdf:value"> \
            <input name="resources__${num}__format" type="text" value="${resource.format}" class="long js-resource-edit-format autocomplete-format" /> \
          </td> \
        </tr> \
        </tr><tr> \
          <td class="dataset-label" property="rdfs:label">'+CKAN.Strings.resourceType+'</td> \
          <td class="dataset-details" property="rdf:value"> \
            {{if resource.resource_type=="file.upload"}} \
              Data File (Uploaded) \
              <input name="resources__${num}__resource_type" type="hidden" value="${resource.resource_type}" /> \
            {{/if}} \
            {{if resource.resource_type!="file.upload"}} \
              <select name="resources__${num}__resource_type" class="short"> \
                {{each resourceTypeOptions}} \
                <option value="${$value[0]}" {{if $value[0]==resource.resource_type}}selected="selected"{{/if}}>${$value[1]}</option> \
                {{/each}} \
              </select> \
            {{/if}} \
          </td> \
        </tr><tr> \
          <td class="dataset-label" property="rdfs:label">'+CKAN.Strings.lastModified+'</td> \
          <td class="dataset-details" property="rdf:value"> \
            <input name="resources__${num}__last_modified" type="text" value="${resource.last_modified}" /> \
            <div class="hint">Dates are in <a href="http://en.wikipedia.org/wiki/ISO_8601#Calendar_dates" target="_blank">ISO Format</a> &mdash; eg. <strong>2012-12-25</strong> or <strong>2010-05-31T14:30</strong>.</div> \
          </td> \
        </tr><tr> \
          <td class="dataset-label" property="rdfs:label">'+CKAN.Strings.sizeBracketsBytes+'</td> \
          <td class="dataset-details" property="rdf:value"> \
            <input name="resources__${num}__size" type="text" value="${resource.size}" class="long" /> \
          </td> \
        </tr><tr> \
          <td class="dataset-label" property="rdfs:label">'+CKAN.Strings.mimetype+' </td> \
          <td class="dataset-details" property="rdf:value"> \
            <input name="resources__${num}__mimetype" type="text" value="${resource.mimetype}" /> \
          </td> \
        </tr><tr> \
          <td class="dataset-label" property="rdfs:label">'+CKAN.Strings.mimetypeInner+'</td> \
          <td class="dataset-details" property="rdf:value"> \
            <input name="resources__${num}__mimetype_inner" type="text" value="${resource.mimetype_inner}" /> \
          </td> \
        </tr><tr> \
          <td class="dataset-label" property="rdfs:label">'+CKAN.Strings.id+'</td> \
          <td class="dataset-details" property="rdf:value"> \
            ${resource.id} \
            <input name="resources__${num}__id" type="hidden" value="${resource.id}" /> \
          </td> \
        </tr><tr> \
          <td class="dataset-label" property="rdfs:label">'+CKAN.Strings.hash+'</td> \
          <td class="dataset-details" property="rdf:value"> \
            ${resource.hash || "Unknown"} \
            <input name="resources__${num}__hash" type="hidden" value="${resource.hash}" /> \
          </td> \
        </tr><tr> \
        <td class="dynamic-extras" colspan="2"> \
          <strong>Extra Fields</strong> \
          <button class="pretty-button add-resource-extra">Add Extra Field</button>\
        </td> \
        </tr> \
      </tbody> \
    </table> \
    <button class="pretty-button danger resource-edit-delete js-resource-edit-delete">Delete Resource</button>\
    </td> \
  </div> \
';

CKAN.Templates.resourceExtra = ' \
  <div class="dynamic-extra"> \
  <button class="pretty-button danger remove-resource-extra">X</button>\
  <input type="text" placeholder="Key" class="extra-key" value="${key}" /> \
  <input type="text" placeholder="Value" class="extra-value" value="${value}" /> \
  </div> \
  ';
