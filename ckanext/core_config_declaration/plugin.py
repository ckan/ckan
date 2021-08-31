import ckan.plugins as p

from ckan.config import Declaration, Option


class CoreConfigDeclarationPlugin(p.SingletonPlugin):
    p.implements(p.IConfigDeclarations)

    def declare_config_options(self, declaration: Declaration, option: Option):

        declaration.declare(option.use, "egg:ckan")
        _declare_devserver(declaration, option)
        _declare_session(declaration, option)
        _declare_repoze(declaration, option)
        _declare_database(declaration, option)
        _declare_site(declaration, option)
        _declare_auth(declaration, option)
        _declare_api_token(declaration, option)
        _declare_search(declaration, option)
        _declare_redis(declaration, option)
        _declare_cors(declaration, option)
        _declare_plugins(declaration, option)
        _declare_views(declaration, option)
        _declare_frontend(declaration, option)
        _declare_package(declaration, option)
        _declare_recaptcha(declaration, option)
        _declare_random(declaration, option)
        _declare_locale(declaration, option)
        _declare_feed(declaration, option)
        _declare_storage(declaration, option)
        _declare_webassets(declaration, option)
        _declare_activity(declaration, option)
        _declare_email(declaration, option)
        _declare_background_jobs(declaration, option)
        return declaration


def _declare_devserver(declaration: Declaration, option: Option):
    declaration.annotate("Development settings")
    devserver = option.ckan.devserver
    declaration.declare(devserver.host, "localhost")
    declaration.declare(devserver.port, 5000)


def _declare_session(declaration: Declaration, option: Option):
    declaration.annotate("Session settings")

    cache_dir = option.cache_dir
    declaration.declare(cache_dir, "/tmp/%(ckan.site_id)s/")

    session = option.beaker.session
    declaration.declare(session.key, "ckan")
    declaration.declare(
        session.secret, "$app_instance_secret"
    ).set_description(
        "This is the secret token that the beaker library uses"
        " to hash the cookie sent to the client. `ckan generate config` "
        "generates a unique value for this each time it generates a "
        "config file."
    )

    aiu = option.app_instance_uuid
    declaration.declare(aiu, "$app_instance_uuid").set_description(
        "`ckan generate config` generates a unique value"
        " for this each time it generates a config file."
    )


def _declare_repoze(declaration: Declaration, option: Option):
    declaration.annotate("repoze.who settings")
    who = option.who
    declaration.declare(who.config_file, "%(here)s/who.ini")
    declaration.declare(who.log_level, "warning")
    declaration.declare(who.log_file, "%(cache_dir)s/who_log.ini")

    declaration.declare(who.timeout, 86400).comment().set_description(
        "Session timeout (user logged out after period of "
        "inactivity, in seconds). Inactive by default, so the session "
        "doesn't expire."
    )


def _declare_database(declaration: Declaration, option: Option):
    declaration.annotate("Database settings")
    declaration.declare(
        option.sqlalchemy.url,
        "postgresql://ckan_default:pass@localhost/ckan_default",
    )


def _declare_site(declaration: Declaration, option: Option):
    declaration.annotate("Site Settings")
    declaration.declare(option.ckan.site_url)


def _declare_auth(declaration: Declaration, option: Option):
    declaration.annotate("Authorization Settings")

    auth = option.ckan.auth
    declaration.declare(auth.anon_create_dataset, "false")
    declaration.declare(auth.create_unowned_dataset, "false")
    declaration.declare(auth.create_dataset_if_not_in_organization, "false")
    declaration.declare(auth.user_create_groups, "false")
    declaration.declare(auth.user_create_organizations, "false")
    declaration.declare(auth.user_delete_groups, "true")
    declaration.declare(auth.user_delete_organizations, "true")
    declaration.declare(auth.create_user_via_api, "false")
    declaration.declare(auth.create_user_via_web, "true")
    declaration.declare(auth.roles_that_cascade_to_sub_groups, "admin")
    declaration.declare(auth.public_user_details, "true")
    declaration.declare(auth.public_activity_stream_detail, "true")
    declaration.declare(auth.allow_dataset_collaborators, "false")
    declaration.declare(auth.create_default_api_keys, "false")


def _declare_api_token(declaration: Declaration, option: Option):
    declaration.annotate("API Token Settings")

    at = option.api_token
    declaration.declare(at.api_token.nbytes, 60)
    declaration.declare(
        at.api_token.jwt.encode.secret, "string:$app_instance_secret"
    )
    declaration.declare(
        at.api_token.jwt.decode.secret, "string:$app_instance_secret"
    )
    declaration.declare(at.api_token.jwt.algorithm, "HS256")


def _declare_search(declaration: Declaration, option: Option):
    declaration.annotate("Search Settings")
    declaration.declare(option.ckan.site_id, "default")
    declaration.declare(
        option.solr_url, "http://127.0.0.1:8983/solr"
    ).comment()

    declaration.declare(option.solr_timeout, 60)


def _declare_redis(declaration: Declaration, option: Option):
    declaration.annotate("Redis Settings")

    declaration.declare(
        option.ckan.redis.url, "redis://localhost:6379/0"
    ).set_description(
        "URL to your Redis instance, including the database to be used."
    )


def _declare_cors(declaration: Declaration, option: Option):
    declaration.annotate("CORS Settings")

    cors = option.ckan.cors
    declaration.declare(cors.origin_allow_all, True).comment().set_description(
        "If cors.origin_allow_all is true, all origins are allowed."
        " If false, the cors.origin_whitelist is used."
    )
    declaration.declare(
        cors.origin_whitelist, "http://example1.com http://example2.com"
    ).comment().set_description(
        "cors.origin_whitelist is a space separated list of allowed domains."
    )


def _declare_plugins(declaration: Declaration, option: Option):
    declaration.annotate("Plugins Settings")
    declaration.declare(
        option.ckan.plugins, "stats text_view image_view recline_view"
    ).set_description(
        "Note: Add ``datastore`` to enable the CKAN DataStore. "
        "Add ``datapusher`` to enable DataPusher. "
        "Add ``resource_proxy`` to enable resorce proxying and get around the "
        "same origin policy. ")


def _declare_views(declaration: Declaration, option: Option):
    views = option.ckan.views.default_views
    declaration.declare(
        views, "image_view text_view recline_view"
    ).set_description(
        "Define which views should be created by default"
        " (plugins must be loaded in ckan.plugins)"
    )

    declaration.annotate(
        "Customize which text formats the text_view plugin will show"
    )
    preview = option.ckan.preview
    declaration.declare(preview.json_formats, "json").comment()
    declaration.declare(
        preview.xml_formats, "xml rdf rdf+xml owl+xml atom rss"
    ).comment()
    declaration.declare(preview.text_formats, "txt plain text/plain").comment()

    declaration.declare(
        preview.image_formats, "png jpeg jpg gif"
    ).comment().set_description(
        "Customize which image formats the image_view plugin will show"
    )


def _declare_frontend(declaration: Declaration, option: Option):
    declaration.annotate("Front-End Settings")
    ckan = option.ckan

    declaration.declare(ckan.site_title, "CKAN")
    declaration.declare(ckan.site_logo, "/base/images/ckan-logo.png")
    declaration.declare(ckan.site_description, "")
    declaration.declare(ckan.favicon, "/base/images/ckan.ico")
    declaration.declare(ckan.gravatar_default, "identicon")
    declaration.declare(ckan.preview.direct, "png jpg gif")
    declaration.declare(
        ckan.preview.loadable,
        "html htm rdf+xml owl+xml xml n3 n-triples turtle plain atom csv tsv rss txt json",
    )
    declaration.declare(ckan.display_timezone, "server")


def _declare_package(declaration: Declaration, option: Option):
    declaration.declare(
        option.package_hide_extras, "for_search_index_only"
    ).comment()
    declaration.declare(
        option.package_edit_return_url,
        "http://another.frontend/dataset/<NAME>",
    ).comment()
    declaration.declare(
        option.package_new_return_url, "http://another.frontend/dataset/<NAME>"
    ).comment()


def _declare_recaptcha(declaration: Declaration, option: Option):
    declaration.declare(option.ckan.recaptcha.publickey).comment()
    declaration.declare(option.ckan.recaptcha.privatekey).comment()


def _declare_random(declaration: Declaration, option: Option):
    declaration.declare(
        option.licenses_group_url,
        "http://licenses.opendefinition.org/licenses/groups/ckan.json",
    ).comment()
    declaration.declare(option.ckan.template_footer_end).comment()


def _declare_locale(declaration: Declaration, option: Option):
    declaration.annotate("Internationalisation Settings")

    ckan = option.ckan
    declaration.declare(ckan.locale_default, "en")
    declaration.declare(
        ckan.locale_order,
        "en pt_BR ja it cs_CZ ca es fr el sv sr sr@latin no sk fi ru de pl nl bg ko_KR hu sa sl lv",
    )
    declaration.declare(ckan.locales_offered)
    declaration.declare(ckan.locales_filtered_out, "en_GB")


def _declare_feed(declaration: Declaration, option: Option):
    declaration.annotate("Feeds Settings")

    feed = option.ckan.feeds
    declaration.declare(feed.authority_name)
    declaration.declare(feed.date)
    declaration.declare(feed.author_name)
    declaration.declare(feed.author_link)


def _declare_storage(declaration: Declaration, option: Option):
    declaration.annotate("Storage Settings")
    ckan = option.ckan

    declaration.declare(ckan.storage_path, "/var/lib/ckan").comment()
    declaration.declare(ckan.max_resource_size, "10").comment()
    declaration.declare(ckan.max_image_size, "2").comment()


def _declare_webassets(declaration: Declaration, option: Option):
    declaration.annotate("Webassets Settings")

    wa = option.ckan.webassets
    declaration.declare(wa.use_x_sendfile, "false").comment()
    declaration.declare(wa.path, "/var/lib/ckan/webassets").comment()


def _declare_activity(declaration: Declaration, option: Option):
    declaration.annotate("Activity Streams Settings")

    ckan = option.ckan
    declaration.declare(ckan.activity_streams_enabled, "true").comment()
    declaration.declare(ckan.activity_list_limit, "31").comment()
    declaration.declare(
        ckan.activity_streams_email_notifications, "true"
    ).comment()
    declaration.declare(ckan.email_notifications_since, "2 days").comment()
    declaration.declare(ckan.hide_activity_from_users, "%(ckan.site_id)s")


def _declare_email(declaration: Declaration, option: Option):
    declaration.annotate("Email settings")
    declaration.declare(option.email_to, "errors@example.com").comment()
    declaration.declare(
        option.error_email_from, "ckan-errors@example.com"
    ).comment()

    smtp = option.smtp
    declaration.declare(smtp.server, "localhost").comment()
    declaration.declare(smtp.starttls, "False").comment()
    declaration.declare(smtp.user, "username@example.com").comment()
    declaration.declare(smtp.password, "your_password").comment()
    declaration.declare(smtp.mail_from, "").comment()
    declaration.declare(smtp.reply_to, "").comment()


def _declare_background_jobs(declaration: Declaration, option: Option):
    declaration.annotate("Background Job Settings")
    jobs = option.ckan.jobs
    declaration.declare(jobs.timeout, 180)
