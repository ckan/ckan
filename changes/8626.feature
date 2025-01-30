:ref:`ckan.user.unique_email_states` can be used to specify statuses of user
accounts that are used for checking uniqueness of the email during
registration. After changing the value of the option, run `ckan db
duplicate_emails` CLI command to verify that all existing emails are still
unique.
