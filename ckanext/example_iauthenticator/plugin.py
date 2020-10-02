# encoding: utf-8

from flask import Blueprint, make_response

from ckan import plugins as p


toolkit = p.toolkit


blueprint = Blueprint(u'example_iauthenticator', __name__, url_prefix=u'/user')


def custom_login():

    return u'logged in'


def custom_logout():

    return u'logged out'


blueprint.add_url_rule(u'/custom_login', view_func=custom_login)
blueprint.add_url_rule(u'/custom_logout', view_func=custom_logout)


class ExampleIAuthenticatorPlugin(p.SingletonPlugin):

    p.implements(p.IAuthenticator)
    p.implements(p.IBlueprint)

    # IAuthenticator

    def identify(self):

        if toolkit.request.path not in [
                toolkit.url_for(u'user.login'),
                toolkit.url_for(u'user.logout'),
                toolkit.url_for(u'example_iauthenticator.custom_login'),
                toolkit.url_for(u'example_iauthenticator.custom_logout')]:
            response = make_response(toolkit.request.path)
            response.set_cookie(u'example_iauthenticator', u'hi')

            return response

    def login(self):

        return toolkit.redirect_to(u'example_iauthenticator.custom_login')

    def logout(self):

        return toolkit.redirect_to(u'example_iauthenticator.custom_logout')

    # IBlueprint

    def get_blueprint(self):

        return [blueprint]
