CKAN config options are not shared with Flask application by default. To pass
option into Flask application(for example, when configuring Flask extension),
add ``flask: true`` to the declaration of the config option.
