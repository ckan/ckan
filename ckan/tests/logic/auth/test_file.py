from __future__ import annotations

from typing import Any
import pytest

import ckan.plugins.toolkit as tk
from ckan import types
from ckan.tests.helpers import call_action

# operation == "file_transfer" and config["ckan.files.owner.transfer_as_update"]
# operation == "file_scan" and config["ckan.files.owner.scan_as_update"]


@pytest.mark.usefixtures("non_clean_db")
class TestPermissionManage:
    def test_anonymous_is_not_allowed(self):
        """Anonymous users are not allowed to manage files."""
        with pytest.raises(tk.NotAuthorized):
            tk.check_access("permission_manage_files", {"user": ""}, {})

    def test_authenticated_is_not_allowed(self, user: dict[str, Any]):
        """Authenticated users are not allowed to manage files."""
        with pytest.raises(tk.NotAuthorized):
            tk.check_access("permission_manage_files", {"user": user["name"]}, {})


@pytest.mark.usefixtures("non_clean_db")
class TestPermissionOwns:
    def test_anonymous_is_not_allowed(self, file: dict[str, Any]):
        """Anonymous users is not an owner."""
        with pytest.raises(tk.NotAuthorized):
            tk.check_access("permission_owns_file", {"user": ""}, {"id": file["id"]})

    def test_authenticated_is_not_allowed(
        self, user: dict[str, Any], file: dict[str, Any]
    ):
        """Authenticated users is not an owner."""
        with pytest.raises(tk.NotAuthorized):
            tk.check_access(
                "permission_owns_file", {"user": user["name"]}, {"id": file["id"]}
            )

    def test_owner_is_allowed(
        self, user: dict[str, Any], file_factory: types.TestFactory
    ):
        """Owners users is identified."""
        file = file_factory(user=user)
        tk.check_access(
            "permission_owns_file", {"user": user["name"]}, {"id": file["id"]}
        )


@pytest.mark.usefixtures("non_clean_db")
class BasePermission:
    action: str

    def test_anonymous_is_not_allowed(self, file: dict[str, Any]):
        """Anonymous user does not have permission."""
        with pytest.raises(tk.NotAuthorized):
            tk.check_access(self.action, {"user": ""}, {"id": file["id"]})

    def test_authenticated_is_not_allowed(
        self, user: dict[str, Any], file: dict[str, Any]
    ):
        """Authenticated user does not have permission."""
        with pytest.raises(tk.NotAuthorized):
            tk.check_access(self.action, {"user": user["name"]}, {"id": file["id"]})

    def test_owner_is_allowed(
        self, user: dict[str, Any], file_factory: types.TestFactory
    ):
        """File owner has permission for owned file."""
        file = file_factory(user=user)
        tk.check_access(self.action, {"user": user["name"]}, {"id": file["id"]})

    @pytest.mark.ckan_config("ckan.files.owner.cascade_access", {})
    def test_owner_without_cascade_is_not_allowed(
        self,
        user: dict[str, Any],
        file_factory: types.TestFactory,
        package_factory: types.TestFactory,
    ):
        """Entity owners do not have permissions for file owned by entity without cascade."""
        package = package_factory(user=user)
        file = file_factory(user=user)
        call_action(
            "file_ownership_transfer",
            id=file["id"],
            owner_type="package",
            owner_id=package["id"],
        )
        with pytest.raises(tk.NotAuthorized):
            tk.check_access(self.action, {"user": user["name"]}, {"id": file["id"]})

    def test_owner_with_cascade_is_allowed(
        self,
        user: dict[str, Any],
        file_factory: types.TestFactory,
        package_factory: types.TestFactory,
    ):
        """Entity owners have permissions for file owned by entity with cascade."""
        package = package_factory(user=user)
        file = file_factory(user=user)
        call_action(
            "file_ownership_transfer",
            id=file["id"],
            owner_type="package",
            owner_id=package["id"],
        )
        tk.check_access(self.action, {"user": user["name"]}, {"id": file["id"]})


class TestPermissionEdit(BasePermission):
    action = "permission_edit_file"


class TestPermissionDelete(BasePermission):
    action = "permission_delete_file"


class TestPermissionRead(BasePermission):
    action = "permission_read_file"


class TestPermissionDownload(BasePermission):
    action = "permission_download_file"


@pytest.mark.usefixtures("non_clean_db")
class TestFileCreate:
    def test_anonymous_uploads_are_not_allowed(self):
        """Anonymous users are not allowed to upload files."""
        with pytest.raises(tk.NotAuthorized):
            tk.check_access("file_create", {"user": ""}, {"storage": "test"})

    def test_authenticated_uploads_are_not_allowed_by_default(
        self, user: dict[str, Any]
    ):
        """Authenticated users are not allowed to upload files with default settings."""
        with pytest.raises(tk.NotAuthorized):
            tk.check_access("file_create", {"user": user["name"]}, {"storage": "test"})

    @pytest.mark.ckan_config("ckan.files.authenticated_uploads.allow", True)
    @pytest.mark.ckan_config("ckan.files.authenticated_uploads.storages", ["test"])
    def test_authenticated_uploads_can_be_enabled(self, user: dict[str, Any]):
        """Authenticated users can upload files if corresponding option is enabled."""
        tk.check_access("file_create", {"user": user["name"]}, {"storage": "test"})


@pytest.mark.usefixtures("non_clean_db")
class TestFileSearch:
    def test_anonymous_search_is_not_allowed(self):
        """Anonymous users are not allowed to search files."""
        with pytest.raises(tk.NotAuthorized):
            tk.check_access("file_create", {"user": ""}, {"storage": "test"})

    def test_authenticated_search_is_not_allowed(self, user: dict[str, Any]):
        """Authenticated users are not allowed to search files."""
        with pytest.raises(tk.NotAuthorized):
            tk.check_access("file_create", {"user": user["name"]}, {"storage": "test"})


@pytest.mark.usefixtures("non_clean_db")
class BaseOperation:
    action: str

    def test_anonymous_is_not_allowed(self, file: dict[str, Any]):
        """Anonymous users are not allowed to perform operation."""
        with pytest.raises(tk.NotAuthorized):
            tk.check_access(self.action, {"user": ""}, {"id": file["id"]})

    def test_authenticated_is_not_allowed(
        self, user: dict[str, Any], file: dict[str, Any]
    ):
        """Authenticated users are not allowed to perform operation."""
        with pytest.raises(tk.NotAuthorized):
            tk.check_access(self.action, {"user": user["name"]}, {"id": file["id"]})

    def test_owner_is_allowed(
        self, user: dict[str, Any], file_factory: types.TestFactory
    ):
        """Owners users are allowed to perform operation."""
        file = file_factory(user=user)
        tk.check_access(self.action, {"user": user["name"]}, {"id": file["id"]})


class TestFileDelete(BaseOperation):
    action = "file_delete"


class TestFileShow(BaseOperation):
    action = "file_show"


class TestFileRename(BaseOperation):
    action = "file_rename"


class TestFilePin(BaseOperation):
    action = "file_pin"


class TestFileUnpin(BaseOperation):
    action = "file_unpin"


@pytest.mark.usefixtures("non_clean_db")
class TestOwnershipTransfer:
    def test_anonymous_transfer_is_not_allowed(self, file: dict[str, Any]):
        """Anonymous users are not allowed to transfer files."""
        with pytest.raises(tk.NotAuthorized):
            tk.check_access(
                "file_ownership_transfer",
                {"user": ""},
                {
                    "id": file["id"],
                    "owner_id": file["owner_id"],
                    "owner_type": file["owner_type"],
                },
            )

    def test_authenticated_transfer_is_not_allowed(
        self, user: dict[str, Any], file: dict[str, Any]
    ):
        """Authenticated users are not allowed to transfer files."""
        with pytest.raises(tk.NotAuthorized):
            tk.check_access(
                "file_ownership_transfer",
                {"user": user["name"]},
                {
                    "id": file["id"],
                    "owner_id": file["owner_id"],
                    "owner_type": file["owner_type"],
                },
            )

    def test_owner_transfer_is_allowed_when_unpinned(
        self, user: dict[str, Any], file_factory: types.TestFactory
    ):
        """Owners users are not allowed to transfer pinned files."""
        file = file_factory(user=user)

        tk.check_access(
            "file_ownership_transfer",
            {"user": user["name"]},
            {
                "id": file["id"],
                "owner_id": file["owner_id"],
                "owner_type": file["owner_type"],
                "force": False,
            },
        )

        call_action("file_pin", id=file["id"])
        with pytest.raises(tk.NotAuthorized):
            tk.check_access(
                "file_ownership_transfer",
                {"user": user["name"]},
                {
                    "id": file["id"],
                    "owner_id": file["owner_id"],
                    "owner_type": file["owner_type"],
                    "force": False,
                },
            )

        tk.check_access(
            "file_ownership_transfer",
            {"user": user["name"]},
            {
                "id": file["id"],
                "owner_id": file["owner_id"],
                "owner_type": file["owner_type"],
                "force": True,
            },
        )

    @pytest.mark.ckan_config("ckan.files.owner.transfer_as_update", False)
    def test_owner_transparent_transfer(
        self,
        user: dict[str, Any],
        file_factory: types.TestFactory,
        package_factory: types.TestFactory,
    ):
        """Transfer does not work without transfer-as-update because of missing auth function."""
        package = package_factory(user=user)
        file = file_factory(user=user)
        with pytest.raises(ValueError):
            tk.check_access(
                "file_ownership_transfer",
                {"user": user["name"]},
                {
                    "id": file["id"],
                    "owner_id": package["id"],
                    "owner_type": "package",
                    "force": False,
                },
            )

    def test_owner_transfer_as_update(
        self,
        user: dict[str, Any],
        file_factory: types.TestFactory,
        package_factory: types.TestFactory,
    ):
        """Enabled transfer-as-update allows transfer without additional code."""
        package = package_factory(user=user)
        file = file_factory(user=user)
        tk.check_access(
            "file_ownership_transfer",
            {"user": user["name"]},
            {
                "id": file["id"],
                "owner_id": package["id"],
                "owner_type": "package",
                "force": False,
            },
        )


class TestOwnerScan:
    def test_anonymous_scan_is_not_allowed(self, file: dict[str, Any]):
        """Anonymous users are not allowed to scan owners."""
        with pytest.raises(tk.NotAuthorized):
            tk.check_access(
                "file_owner_scan",
                {"user": ""},
                {
                    "owner_id": file["owner_id"],
                    "owner_type": file["owner_type"],
                },
            )

    def test_authenticated_scan_is_not_allowed(
        self, user: dict[str, Any], file: dict[str, Any]
    ):
        """Authenticated users are not allowed to scan owners."""
        with pytest.raises(tk.NotAuthorized):
            tk.check_access(
                "file_owner_scan",
                {"user": user["name"]},
                {
                    "owner_id": file["owner_id"],
                    "owner_type": file["owner_type"],
                },
            )

    @pytest.mark.ckan_config("ckan.files.owner.scan_as_update", False)
    def test_owner_transparent_scan(
        self,
        user: dict[str, Any],
        package_factory: types.TestFactory,
    ):
        """Scan does not work without scan-as-update because of missing auth function."""
        package = package_factory(user=user)
        with pytest.raises(ValueError):
            tk.check_access(
                "file_owner_scan",
                {"user": user["name"]},
                {
                    "owner_id": package["id"],
                    "owner_type": "package",
                },
            )

    def test_owner_scan_as_update(
        self,
        user: dict[str, Any],
        package_factory: types.TestFactory,
    ):
        """Enabled scan-as-update allows scan without additional code."""
        package = package_factory(user=user)
        tk.check_access(
            "file_owner_scan",
            {"user": user["name"]},
            {
                "owner_id": package["id"],
                "owner_type": "package",
            },
        )
