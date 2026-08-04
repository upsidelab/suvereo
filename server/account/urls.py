from django.urls import path

import account.views.accounts
import account.views.dataset_roles
import account.views.groups
import account.views.login
import account.views.permissions
import account.views.service_accounts
import account.views.users

urlpatterns = [
    path("api/auth/login", account.views.login.LoginView.as_view(), name="login"),
    path("api/account", account.views.accounts.AccountView.as_view(), name="account"),
    path("api/groups", account.views.groups.GroupListView.as_view(), name="group_list"),
    path("api/groups/<int:group_id>", account.views.groups.GroupDetailView.as_view(), name="group_detail"),
    path("api/groups/<int:group_id>/members", account.views.groups.GroupMembersView.as_view(), name="group_members"),
    path(
        "api/groups/<int:group_id>/members/<int:user_id>",
        account.views.groups.GroupMemberDetailView.as_view(),
        name="group_member_detail",
    ),
    path("api/permissions", account.views.permissions.PermissionListView.as_view(), name="permission_list"),
    path("api/dataset-roles", account.views.dataset_roles.DatasetRoleListView.as_view(), name="dataset_role_list"),
    path(
        "api/dataset-roles/<int:dataset_role_id>",
        account.views.dataset_roles.DatasetRoleDetailView.as_view(),
        name="dataset_role_detail",
    ),
    path(
        "api/dataset-roles/<int:dataset_role_id>/usage",
        account.views.dataset_roles.DatasetRoleUsageView.as_view(),
        name="dataset_role_usage",
    ),
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
]
