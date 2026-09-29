from django.urls import path
from rest_framework_simplejwt.views import TokenBlacklistView, TokenRefreshView

import account.views.accounts
import account.views.admins
import account.views.dataset_access
import account.views.dataset_roles
import account.views.global_role_groups
import account.views.global_role_members
import account.views.global_roles
import account.views.group_global_roles
import account.views.group_members
import account.views.groups
import account.views.login
import account.views.permissions
import account.views.service_accounts
import account.views.users

urlpatterns = [
    path("api/auth/login", account.views.login.LoginView.as_view(), name="login"),
    path("api/auth/token/refresh", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/auth/logout", TokenBlacklistView.as_view(), name="logout"),
    path("api/account", account.views.accounts.AccountView.as_view(), name="account"),
    path("api/admins", account.views.admins.AdminListView.as_view(), name="admin_list"),
    path("api/users", account.views.users.UserListView.as_view(), name="user_list"),
    path("api/users/<int:id>", account.views.users.UserView.as_view(), name="user_details"),
    path("api/users/<int:id>/password", account.views.users.UserPasswordView.as_view(), name="user_password"),
    path(
        "api/service_accounts/",
        account.views.service_accounts.ServiceAccountListView.as_view(),
        name="service_account_list",
    ),
    path("api/service_accounts/<int:id>", account.views.service_accounts.ServiceAccountView.as_view()),
    path(
        "api/service_accounts/<int:id>/reset_token",
        account.views.service_accounts.ResetTokenView.as_view(),
        name="reset_token",
    ),
    path(
        "api/service_accounts/check_name",
        account.views.service_accounts.CheckServiceNameView.as_view(),
        name="check_service_name",
    ),
    path("api/global_roles", account.views.global_roles.GlobalRoleListView.as_view(), name="global_role_list"),
    path("api/global_roles/<int:id>", account.views.global_roles.GlobalRoleDetailView.as_view(), name="global_role_details"),
    path(
        "api/global_roles/<int:id>/members",
        account.views.global_role_members.GlobalRoleMemberListView.as_view(),
        name="global_role_member_list",
    ),
    path(
        "api/global_roles/<int:id>/members/<int:user_id>",
        account.views.global_role_members.GlobalRoleMemberDetailView.as_view(),
        name="global_role_member_details",
    ),
    path(
        "api/global_roles/<int:id>/groups",
        account.views.global_role_groups.GlobalRoleGroupListView.as_view(),
        name="global_role_group_list",
    ),
    path(
        "api/global_roles/<int:id>/groups/<int:group_id>",
        account.views.global_role_groups.GlobalRoleGroupDetailView.as_view(),
        name="global_role_group_details",
    ),
    path("api/groups", account.views.groups.GroupListView.as_view(), name="group_list"),
    path("api/groups/<int:id>", account.views.groups.GroupDetailView.as_view(), name="group_details"),
    path(
        "api/groups/<int:id>/members",
        account.views.group_members.GroupMemberListView.as_view(),
        name="group_member_list",
    ),
    path(
        "api/groups/<int:id>/members/<int:user_id>",
        account.views.group_members.GroupMemberDetailView.as_view(),
        name="group_member_details",
    ),
    path(
        "api/groups/<int:id>/global_roles",
        account.views.group_global_roles.GroupGlobalRoleListView.as_view(),
        name="group_global_role_list",
    ),
    path(
        "api/groups/<int:id>/global_roles/<int:global_role_id>",
        account.views.group_global_roles.GroupGlobalRoleDetailView.as_view(),
        name="group_global_role_details",
    ),
    path("api/data_set_roles", account.views.dataset_roles.DatasetRoleListView.as_view(), name="dataset_role_list"),
    path(
        "api/data_set_roles/<int:id>",
        account.views.dataset_roles.DatasetRoleDetailView.as_view(),
        name="dataset_role_details",
    ),
    path("api/permissions", account.views.permissions.PermissionListView.as_view(), name="permission_list"),
    path(
        "api/data_sets/<int:data_set_id>/roles/",
        account.views.dataset_access.DatasetAccessListView.as_view(),
        name="dataset_access_list",
    ),
    path(
        "api/data_sets/<int:data_set_id>/roles/<int:role_id>/members",
        account.views.dataset_access.DatasetRoleMemberListView.as_view(),
        name="dataset_role_member_list",
    ),
    path(
        "api/data_sets/<int:data_set_id>/roles/<int:role_id>/members/<int:user_id>",
        account.views.dataset_access.DatasetRoleMemberView.as_view(),
        name="dataset_role_member_details",
    ),
    path(
        "api/data_sets/<int:data_set_id>/roles/<int:role_id>/groups",
        account.views.dataset_access.DatasetRoleGroupListView.as_view(),
        name="dataset_role_group_list",
    ),
    path(
        "api/data_sets/<int:data_set_id>/roles/<int:role_id>/groups/<int:group_id>",
        account.views.dataset_access.DatasetRoleGroupView.as_view(),
        name="dataset_role_group_details",
    ),
]
