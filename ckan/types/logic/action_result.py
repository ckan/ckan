# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import (
    Any, List, Optional, Tuple, Union
)
from typing_extensions import TypeAlias

from ..model import Query, Model

AnyDict: TypeAlias = "dict[str, Any]"
###############################################################################
#                                     get                                     #
###############################################################################
PackageList = List[str]
CurrentPackageListWithResources = List[AnyDict]
MemberList = List[Tuple[Any, ...]]
PackageCollaboratorList = List[AnyDict]
PackageCollaboratorListForUser = PackageCollaboratorList
GroupList = List[AnyDict]
OrganizationList = List[AnyDict]
GroupListAuthz = List[AnyDict]
OrganizationListForUser = List[AnyDict]
LicenseList = List[AnyDict]
TagList = Union[List[AnyDict], List[str]]
UserList = Union[List[AnyDict], List[str], "Query[Model.User]"]
PackageRelationshipsList = List[AnyDict]
PackageShow = AnyDict
ResourceShow = AnyDict
ResourceViewShow = AnyDict
ResourceViewList = List[AnyDict]
GroupShow = AnyDict
OrganizationShow = AnyDict
GroupPackageShow = List[AnyDict]
TagShow = AnyDict
UserShow = AnyDict
PackageAutocomplete = List[AnyDict]
FormatAutocomplete = List[str]
UserAutocomplete = List[AnyDict]
GroupAutocomplete = List[AnyDict]
OrganizationAutocomplete = List[AnyDict]
PackageSearch = AnyDict
ResourceSearch = AnyDict
TagSearch = AnyDict
TagAutocomplete = List[str]
TaskStatusShow = AnyDict
TermTranslationShow = List[AnyDict]
GetSiteUser = AnyDict
StatusShow = AnyDict
VocabularyList = List[AnyDict]
VocabularyShow = AnyDict
UserFollowerCount = int
DatasetFollowerCount = int
GroupFollowerCount = int
OrganizationFollowerCount = int
UserFollowerList = List[AnyDict]
DatasetFollowerList = List[AnyDict]
GroupFollowerList = List[AnyDict]
OrganizationFollowerList = List[AnyDict]
AmFollowingUser = bool
AmFollowingDataset = bool
AmFollowingGroup = bool
FolloweeCount = int
UserFolloweeCount = int
DatasetFolloweeCount = int
GroupFolloweeCount = int
OrganizationFolloweeCount = int
FolloweeList = List[AnyDict]
UserFolloweeList = List[AnyDict]
DatasetFolloweeList = List[AnyDict]
GroupFolloweeList = List[AnyDict]
OrganizationFolloweeList = List[AnyDict]
DashboardNewActivitiesCount = int
MemberRolesList = List[AnyDict]
HelpShow = Optional[str]
ConfigOptionShow = Any
ConfigOptionList = List[str]
JobList = List[AnyDict]
JobShow = AnyDict
ApiTokenList = List[AnyDict]

###############################################################################
#                                    create                                   #
###############################################################################
PackageCreate = Union[AnyDict, str]
ResourceCreate = AnyDict
ResourceViewCreate = AnyDict
ResourceCreateDefaultResourceViews = List[AnyDict]
PackageCreateDefaultResourceViews = List[AnyDict]
PackageRelationshipCreate = AnyDict
MemberCreate = AnyDict
PackageCollaboratorCreate = AnyDict
GroupCreate = Union[str, AnyDict]
OrganizationCreate = Union[str, AnyDict]
UserCreate = AnyDict
UserInvite = AnyDict
VocabularyCreate = AnyDict
TagCreate = AnyDict
FollowUser = AnyDict
FollowDataset = AnyDict
GroupOrOrgMemberCreate = AnyDict
GroupMemberCreate = AnyDict
OrganizationMemberCreate = AnyDict
FollowGroup = AnyDict
ApiTokenCreate = AnyDict

###############################################################################
#                                    delete                                   #
###############################################################################
UserDelete: TypeAlias = None
PackageDelete: TypeAlias = None
DatasetPurge: TypeAlias = None
ResourceDelete: TypeAlias = None
ResourceViewDelete: TypeAlias = None
ResourceViewClear: TypeAlias = None
PackageRelationshipDelete: TypeAlias = None
MemberDelete: TypeAlias = None
PackageCollaboratorDelete: TypeAlias = None
GroupDelete: TypeAlias = None
OrganizationDelete: TypeAlias = None
ApiTokenRevoke: TypeAlias = None

###############################################################################
#                                    patch                                    #
###############################################################################
PackagePatch = Union[str, AnyDict]
ResourcePatch = AnyDict
GroupPatch = AnyDict
OrganizationPatch = AnyDict
UserPatch = AnyDict

###############################################################################
#                                    update                                   #
###############################################################################
ResourceUpdate = AnyDict
ResourceViewUpdate = AnyDict
ResourceViewReorder = AnyDict
PackageUpdate = Union[str, AnyDict]
ConfigOptionUpdate = AnyDict
PackageRevise = AnyDict
PackageResourceReorder = AnyDict
PackageRelationshipUpdate = AnyDict
GroupUpdate = AnyDict
OrganizationUpdate = AnyDict
UserUpdate = AnyDict
UserGenerateApikey = AnyDict
TaskStatusUpdate = AnyDict
TaskStatusUpdateMany = AnyDict
TermTranslationUpdate = AnyDict
TermTranslationUpdateMany = AnyDict
VocabularyUpdate = AnyDict
DashboardMarkActivitiesOld: TypeAlias = None
SendEmailNotifications: TypeAlias = None
PackageOwnerOrgUpdate: TypeAlias = None
BulkUpdatePrivate: TypeAlias = None
BulkUpdatePublic: TypeAlias = None
BulkUpdateDelete: TypeAlias = None
