Validators registered via :py:class:`~ckan.plugins.interfaces:IValidators` can
be used in config declarations. Note that custom config options(declared by
plugins), may remain not normalized at this point and must be converted
manually::

    def get_validators(self):
        validators = {}
        use_fancy = tk.asbool(tk.config.get("my.ext.use_fancy_validator"))
        if use_fancy:
            validators["fancy_validator"] = fancy_validator
        return validators
