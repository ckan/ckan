
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
  <div class="alert-message block-message" style="display: none;"></div> \
  </div> \
</div> \
';



CKAN.Templates.resourceEntry = ' \
  <li class="ui-state-default resource-edit"> \
    <div class="drag-bars">|||</div> \
    <a class="resource-edit-expand js-resource-edit-toggle" href="#">${resource.name}</a>\
  </li> \
  <!-- \
  <td class="resource-edit-delete"> \
    <a class="resource-edit-delete js-resource-edit-delete" href="#"><img src="/images/icons/delete.png" /></a> \
  </td> \
  --> \
';


CKAN.Templates.resourceTable = ' \
  <div style="display: none;" class="resource-details js-resource-edit-expanded"> \
    <table> \
      <thead> \
        <tr> \
          <th>Field</th> \
          <th>Value</th> \
        </tr> \
      </thead> \
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
            <textarea name="resources__${num}__description" type="text">${resource.description}</textarea> \
          </td> \
        </tr> \
        <tr> \
          <td class="dataset-label" property="rdfs:label">'+CKAN.Strings.url+'</td> \
          <td class="dataset-details" property="rdf:value"> \
            {{if resource.resource_type=="file.upload"}} \
              ${resource.url} \
              <input name="resources__${num}__url" type="hidden" value="${resource.url}" /> \
            {{/if}} \
            {{if resource.resource_type!="file.upload"}} \
              <input name="resources__${num}__url" type="text" value="${resource.url}" class="long" /> \
            {{/if}} \
          </td> \
        </tr> \
        </tr><tr> \
          <td class="dataset-label" property="rdfs:label">'+CKAN.Strings.format+'</td> \
          <td class="dataset-details" property="rdf:value"> \
            <input name="resources__${num}__format" type="text" value="${resource.format}" class="long autocomplete-format" /> \
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
        </tr> \
      </tbody> \
    </table> \
  </div> \
';

