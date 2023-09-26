import factory
from pytest_factoryboy import register

from ckan.tests.factories import User

@register(_name="user_info")
class UserInfoFactory(factory.DictFactory):
    sub = factory.Faker("uuid4")
    name = factory.Faker("name")
    email = factory.Faker("email")


@register
class UserFactory(User):
    pass
