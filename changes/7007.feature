Added user, group, and organization view functions and templates to make organization/group membership more public.

Group and Organization lists now show the number of members.

Group and Organization lists on a user's profile and dashboard now display the role for the group.

Refactor: renamed `<group|organization>.members` to `<group|organization>.manage_members`. `<group|organization>.members` is no longer an admin page.

New: `read_groups` and `read_organization` view functions and templates for users. Adds group and organization tabs to a user profile to list the groups they belong to.

New: `member_dump` view function. Downloads group/organization members into a CSV file with headers [Username,Email,Name,Role]
