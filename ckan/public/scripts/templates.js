
CKAN.Templates.resourceAddChoice = ' \
  <ul> \
    <li>Add a resource:</li> \
    <li><a href="#" action="upload-file" class="action-resource-tab">Upload a file</a></li> \
    <li><a href="#" action="link-file" class="action-resource-tab">Link to a file</a></li> \
    <li><a href="#" action="link-api" class="action-resource-tab">Link to an API</a></li> \
  </ul> \
';

CKAN.Templates.resourceAddLinkFile = ' \
  <form class="resource-add" action=""> \
    <dl> \
      <dt> \
        <label class="field_opt" for="url"> \
          File URL \
        </label> \
      </dt> \
      <dd> \
        <input name="url" type="text" placeholder="http://mydataset.com/file.csv" style="width: 60%"/> \
        <input name="save" type="submit" class="pretty primary" value="Add" /> \
        <input name="reset" type="reset" class="pretty" value="Cancel" /> \
      </dd> \
    </dl> \
     \
  </form> \
';

CKAN.Templates.resourceAddLinkApi = ' \
  <form class="resource-add" action=""> \
    <dl> \
      <dt> \
        <label class="field_opt" for="url"> \
          Api URL \
        </label> \
      </dt> \
      <dd> \
        <input name="url" type="text" placeholder="http://mydataset.com/file.csv" style="width: 60%" /> \
        <input name="save" type="submit" class="pretty primary" value="Add" /> \
        <input name="reset" type="reset" class="pretty" value="Cancel" /> \
      </dd> \
    </dl> \
     \
  </form> \
';

CKAN.Templates.resourceUpload = ' \
  <form action="http://test-ckan-net-storage.commondatastorage.googleapis.com/" class="resource-upload" \
    enctype="multipart/form-data" \
    method="POST"> \
 \
    <dl> \
      <dt> \
        <label class="field_opt fileinput-button" for="file"> \
          File \
        </label> \
      </dt> \
      <dd> \
        <input type="file" name="file" /> \
        <span class="fileinfo"></span> \
        <input id="upload" name="upload" type="submit" class="pretty primary" value="Add" /> \
        <input id="reset" name="reset" type="reset" class="pretty" value="Cancel" /> \
      </dd> \
    </dl> \
  </form> \
  <div class="messages" style="display: none;"></div> \
  </div> \
';

CKAN.Templates.resourceEntry = ' \
  <tr> \
  <td class="resource-url"> \
    <input name="resources__${num}__url" type="text" value="${url}" class="short" /> \
  </td> \
  <td class="resource-format"> \
    <input name="resources__${num}__format" type="text" value="" class="autocomplete-format short" /> \
  </td> \
  <td class="resource-description"> \
    <input name="resources__${num}__description" type="text" value="" class="medium-width" /> \
  </td> \
  <td class="resource-hash"> \
    <input name="resources__${num}__hash" type="text" value="" class="short" /> \
  </td> \
  <td class="resource-id"> \
    <input name="resources__${num}__id" type="hidden" value="" /> \
  </td> \
</tr> \
';
