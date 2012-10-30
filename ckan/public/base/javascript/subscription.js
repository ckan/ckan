$('#delete_subscription').click(function(event)
{
    $('#subscription-form .return_url').val(document.URL)
    $('#subscription-form').submit()
})

