$('#create_subscription').click(function(event)
{
    post_uri = document.URL.replace(/\/dataset?/, this.attributes['action'].value)
    $('#subscription-form').attr('action', post_uri)
    $('#subscription-form').submit()
})
