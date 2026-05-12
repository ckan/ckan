- Saving a draft dataset is now called "Publish" and an "Unpublish" button is available
to move an active dataset back to the draft state.
- Consistent display of draft state across dataset pages.
- Error handling is now done on publish, so validators that only apply certain rules to fields for published datasets (e.g. required-only-when-published) will be properly displayed instead of causing a server error.
- templates/package/new_package_form.html content has been merged into its parent template templates/package/snippets/package_form.html and is now marked as deprecated.
