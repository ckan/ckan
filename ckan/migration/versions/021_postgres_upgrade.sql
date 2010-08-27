CREATE INDEX idx_extra_pkg_id ON package_extra (package_id);
CREATE INDEX idx_extra_id_pkg_id ON package_extra (id, package_id);

CREATE INDEX idx_group_pkg_id ON package_group (package_id);
CREATE INDEX idx_extra_grp_id_pkg_id ON package_group (group_id, package_id);

CREATE INDEX idx_pkg_id ON package (id);
CREATE INDEX idx_pkg_name ON package (name);
CREATE INDEX idx_pkg_title ON package (title);
CREATE INDEX idx_pkg_lname ON package (lower(name));
CREATE INDEX idx_pkg_uname ON package (upper(name));
CREATE INDEX idx_pkg_rev_id ON package (revision_id);

CREATE INDEX idx_pkg_sid ON package (id,state);
CREATE INDEX idx_pkg_sname ON package (name,state);
CREATE INDEX idx_pkg_stitle ON package (title,state);
CREATE INDEX idx_pkg_slname ON package (lower(name),state);
CREATE INDEX idx_pkg_suname ON package (upper(name),state);
CREATE INDEX idx_pkg_srev_id ON package (revision_id,state);

CREATE INDEX idx_pkg_revision_id ON package_revision (id);
CREATE INDEX idx_pkg_revision_name ON package_revision (name);
CREATE INDEX idx_pkg_revision_rev_id ON package_revision (revision_id);

CREATE INDEX idx_rev_state ON revision (state);

CREATE INDEX idx_tag_id ON tag (id);
CREATE INDEX idx_tag_name ON tag (name);

CREATE INDEX idx_package_tag_id ON package_tag (id);
CREATE INDEX idx_package_tag_tag_id ON package_tag (tag_id);
CREATE INDEX idx_package_tag_pkg_id ON package_tag (package_id);
CREATE INDEX idx_package_tag_pkg_id_tag_id ON package_tag (tag_id, package_id);

CREATE INDEX idx_package_tag_revision_id ON package_tag_revision (id);
CREATE INDEX idx_package_tag_revision_tag_id ON package_tag_revision (tag_id);
CREATE INDEX idx_package_tag_revision_rev_id ON package_tag_revision (revision_id);
CREATE INDEX idx_package_tag_revision_pkg_id ON package_tag_revision (package_id);
CREATE INDEX idx_package_tag_revision_pkg_id_tag_id ON package_tag_revision (tag_id, package_id);

CREATE INDEX idx_rating_id ON rating (id);
CREATE INDEX idx_rating_user_id ON rating (user_id);
CREATE INDEX idx_rating_package_id ON rating (package_id);

CREATE INDEX idx_user_id ON "user" (id);
CREATE INDEX idx_user_name ON "user" (name);

CREATE INDEX idx_uor_id ON user_object_role (id);
CREATE INDEX idx_uor_user_id ON user_object_role (user_id);
CREATE INDEX idx_uor_context ON user_object_role (context);
CREATE INDEX idx_uor_role ON user_object_role (role);

CREATE INDEX idx_uor_user_id_role ON user_object_role (user_id,role);
CREATE INDEX idx_ra_role ON role_action (role);
CREATE INDEX idx_ra_action ON role_action (action);
CREATE INDEX idx_ra_role_action ON role_action (action,role);

CREATE INDEX idx_group_id ON "group" (id);
CREATE INDEX idx_group_name ON "group" (name);

CREATE INDEX idx_package_group_id ON package_group (id);
CREATE INDEX idx_package_group_group_id ON package_group (group_id);
CREATE INDEX idx_package_group_pkg_id ON package_group (package_id);
CREATE INDEX idx_package_group_pkg_id_group_id ON package_group (group_id, package_id);

CREATE INDEX idx_package_resource_id ON package_resource (id);
CREATE INDEX idx_package_resource_url ON package_resource (url);
CREATE INDEX idx_package_resource_pkg_id ON package_resource (package_id);
CREATE INDEX idx_package_resource_pkg_id_resource_id ON package_resource (package_id, id);

CREATE INDEX idx_package_resource_rev_id ON package_resource_revision (revision_id);
CREATE INDEX idx_package_extra_rev_id ON package_extra_revision (revision_id);

