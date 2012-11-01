function validate_subscription_name()
{
    var create_form = document.forms.create_subscription_form;
    var subscription_name = create_form.subscription_name.value
    
    $.ajax(
    {
        url: '/subscription/check_name/' + create_form.subscription_name.value,
        dataType: 'text',
        success: function( data )
        {
            if( !data )
            {
                create_form.submit();
                return;
            }

            alert(data);
        }
    });
    
    return false;
}

function set_return_url()
{
    var delete_form = document.forms.delete_subscription_form;
    delete_form.return_url.value = document.URL;
    
    return true;
}

