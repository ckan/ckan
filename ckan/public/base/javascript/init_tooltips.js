// Initialize tooltips using Bootstrap
$(function() {
  $('[data-bs-toggle="tooltip"]').each(function (index, element) {
    bootstrap.Tooltip.getOrCreateInstance(element)
  })
})
