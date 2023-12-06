$.ajax({
    type: "HEAD",
    async: false,
    cache: false,
    url: "/dashboard",
    success: function(message) {
        if (confirm("It looks like you're logged in. This page may be out of date. Reload?")) {
            location.reload();
        }
    }
});
