function submitForm(value) {
    const datasetForm = document.getElementById('dataset-edit');
    const resourceForm = document.getElementById('resource-edit');

    const form = datasetForm || resourceForm;

    if (form) {
      let hiddenInput = document.createElement('input');
      hiddenInput.type = 'hidden';
      hiddenInput.name = 'save';
      hiddenInput.value = value;
      form.appendChild(hiddenInput);

      form.submit();
    } else {
      console.log("No target form found on this page.");
    }
  }