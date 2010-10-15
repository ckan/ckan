from package import *
from package_gov import *
from group import *
from authorization_group import *
from registry import *
from authz import *
from package_dict import *
from harvest_source import *

from ckan.model.types import JsonType
from formalchemy import forms
import formalchemy
forms.FieldSet.default_renderers[JsonType] = formalchemy.fields.TextFieldRenderer
