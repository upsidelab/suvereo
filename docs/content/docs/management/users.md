# Manage Users

A user is a person who signs in to Suvereo with an email address and a password. What a user can do is decided by the [roles](/docs/management/roles-and-groups) they hold, directly or through [groups](/docs/management/roles-and-groups#groups), and by whether they are an admin.

Users are managed under **Manage** → **Users** in the left sidebar. The list shows each user's email, whether the account is active and whether it belongs to an admin.

## Creating a User

Click **New User** and fill in:

- **Email:** the address the user signs in with.
- **Password** and **Confirm Password:** at least 8 characters.
- **Active:** whether the user can sign in. On by default.
- **Admin:** whether the user is an admin, see below. Off by default.

A new user has no access to any data set until they are given a role. Grant one from **Manage** → **Roles**, from the data set's **Manage Access** page, or by adding the user to a group.

## Editing a User

**Edit** changes the email, deactivates or reactivates the account, and turns admin access on or off. Deactivating a user prevents them from signing in and keeps their account and history.

**Change Password** sets a new password for the user.

## Admins

An admin has all permissions, including ones added in later versions, and does not need roles. Admins are separate from roles and groups: admin access is a setting on the account, and an admin cannot be deleted.

Only an admin can create another admin, make a user an admin, deactivate an admin or edit an admin account. When you remove your own admin access, the UI asks you to confirm.

For everything short of full access, use roles instead, which can be limited to specific permissions or to one data set.
