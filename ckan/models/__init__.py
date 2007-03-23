import sqlobject
from pylons.database import PackageHub
hub = PackageHub('ckan')
sqlobject.sqlhub.processConnection = hub.getConnection()

from package import *
import vdm.base
from vdm.base import State

class DomainModel(object):

    # should be in order needed for creation
    classes = [
            License,
            Package,
            PackageRevision,
            Tag,
            TagRevision,
            PackageTag,
            PackageTagRevision,
            ]

    def __init__(self, revision, transaction=None):
        self.revision = revision
        self.transaction = transaction
        self.packages = vdm.base.VersionedDomainObjectRegister(Package, 'name', revision, transaction)
        self.tags = vdm.base.VersionedDomainObjectRegister(Tag, 'name', revision, transaction)
        self.package_tags = vdm.base.VersionedDomainObjectRegister(PackageTag, 'id', revision, transaction)

    @classmethod
    def initialise_repository(self):
        # all OSI licenses from http://www.opensource.org/licenses/
        # but excluding some that have been deprecated by their authors
        # e.g. 'Historical Permission Notice and Disclaimer'
        License(name='OKD Compliant::Public Domain')
        License(name='OKD Compliant::Creative Commons Attribution')
        License(name='OKD Compliant::Creative Commons Attribution-ShareAlike')
        License(name='OKD Compliant::GNU Free Documentation License (GFDL)')
        License(name='OKD Compliant::Other')
        License(name='Non-OKD Compliant::Other')
        License(name='OSI Approved::Academic Free License')
        License(name='OSI Approved::Adaptive Public License')
        License(name='OSI Approved::Apache Software License')
        License(name='OSI Approved::Apache License, 2.0')
        License(name='OSI Approved::Apple Public Source License')
        License(name='OSI Approved::Artistic license')
        License(name='OSI Approved::Attribution Assurance Licenses')
        License(name='OSI Approved::New BSD license')
        License(name='OSI Approved::Computer Associates Trusted Open Source License 1.1')
        License(name='OSI Approved::Common Development and Distribution License')
        License(name='OSI Approved::Common Public License 1.0')
        License(name='OSI Approved::CUA Office Public License Version 1.0')
        License(name='OSI Approved::EU DataGrid Software License')
        License(name='OSI Approved::Eclipse Public License')
        License(name='OSI Approved::Educational Community License')
        License(name='OSI Approved::Eiffel Forum License')
        License(name='OSI Approved::Eiffel Forum License V2.0')
        License(name='OSI Approved::Entessa Public License')
        License(name='OSI Approved::Fair License')
        License(name='OSI Approved::Frameworx License')
        License(name='OSI Approved::GNU General Public License (GPL)')
        License(name='OSI Approved::GNU Library or "Lesser" General Public License (LGPL)')
        License(name='OSI Approved::IBM Public License')
        License(name='OSI Approved::Intel Open Source License')
        License(name='OSI Approved::Jabber Open Source License')
        License(name='OSI Approved::Lucent Public License (Plan9)')
        License(name='OSI Approved::Lucent Public License Version 1.02')
        License(name='OSI Approved::MIT license')
        License(name='OSI Approved::MITRE Collaborative Virtual Workspace License (CVW License)')
        License(name='OSI Approved::Motosoto License')
        License(name='OSI Approved::Mozilla Public License 1.0 (MPL)')
        License(name='OSI Approved::Mozilla Public License 1.1 (MPL)')
        License(name='OSI Approved::NASA Open Source Agreement 1.3')
        License(name='OSI Approved::Naumen Public License')
        License(name='OSI Approved::Nethack General Public License')
        License(name='OSI Approved::Nokia Open Source License')
        License(name='OSI Approved:: OCLC Research Public License 2.0')
        License(name='OSI Approved::Open Group Test Suite License')
        License(name='OSI Approved::Open Software License')
        License(name='OSI Approved::PHP License')
        License(name='OSI Approved::Python license (CNRI Python License)')
        License(name='OSI Approved::Python Software Foundation License')
        License(name='OSI Approved::Qt Public License (QPL)')
        License(name='OSI Approved::RealNetworks Public Source License V1.0')
        License(name='OSI Approved::Reciprocal Public License')
        License(name='OSI Approved::Ricoh Source Code Public License')
        License(name='OSI Approved::Sleepycat License')
        License(name='OSI Approved::Sun Industry Standards Source License (SISSL)')
        License(name='OSI Approved::Sun Public License')
        License(name='OSI Approved::Sybase Open Watcom Public License 1.0')
        License(name='OSI Approved::University of Illinois/NCSA Open Source License')
        License(name='OSI Approved::Vovida Software License v. 1.0')
        License(name='OSI Approved::W3C License')
        License(name='OSI Approved::wxWindows Library License')
        License(name='OSI Approved::X.Net License')
        License(name='OSI Approved::Zope Public License')
        License(name='OSI Approved::zlib/libpng license')

repo = vdm.base.Repository(DomainModel)

