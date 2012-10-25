$('#create_subscription').click(function(event)
{
    post_uri = document.URL.replace(/\/dataset?/, this.attributes['action'].value)
    $('#subscription-form').attr('action', post_uri)
    $('#subscription-form').submit()
})

$('#delete_subscription').click(function(event)
{
    $('#subscription-form .return_url').val(document.URL)
    $('#subscription-form').submit()
})

