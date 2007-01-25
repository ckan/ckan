from sqlobject import *
from pylons.database import PackageHub
hub = PackageHub('ckan')
__connection__ = hub

from package import *
