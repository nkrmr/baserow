from django.contrib.auth.models import AnonymousUser

import pytest

from baserow.contrib.builder.elements.models import Element
from baserow.contrib.builder.elements.operations import ListElementsPageOperationType
from baserow.contrib.builder.elements.permission_manager import (
    ElementVisibilityPermissionManager,
)
from baserow.contrib.builder.workflow_actions.models import BuilderWorkflowAction
from baserow.contrib.builder.workflow_actions.operations import (
    DispatchBuilderWorkflowActionOperationType,
    ListBuilderWorkflowActionsPageOperationType,
)
from baserow.core.types import PermissionCheck
from baserow.core.user_sources.user_source_user import UserSourceUser


@pytest.mark.django_db
def test_element_visibility_permission_manager_check_permission(data_fixture):
    user = data_fixture.create_user(username="Auth user")
    builder = data_fixture.create_builder_application(user=user)
    builder_to = data_fixture.create_builder_application(workspace=None)
    domain1 = data_fixture.create_builder_custom_domain(
        builder=builder, published_to=builder_to
    )

    public_page = data_fixture.create_builder_page(builder=builder_to)

    public_user_source = data_fixture.create_user_source_with_first_type(
        application=builder_to
    )

    element_all = data_fixture.create_builder_button_element(
        page=public_page, visibility=Element.VISIBILITY_TYPES.ALL
    )

    element_logged_in = data_fixture.create_builder_button_element(
        page=public_page, visibility=Element.VISIBILITY_TYPES.LOGGED_IN
    )

    element_not_logged = data_fixture.create_builder_button_element(
        page=public_page, visibility=Element.VISIBILITY_TYPES.NOT_LOGGED
    )

    workflow_action_all = data_fixture.create_local_baserow_create_row_workflow_action(
        page=public_page, element=element_all
    )
    workflow_action_logged_in = (
        data_fixture.create_local_baserow_create_row_workflow_action(
            page=public_page, element=element_logged_in
        )
    )
    workflow_action_not_logged = (
        data_fixture.create_local_baserow_create_row_workflow_action(
            page=public_page, element=element_not_logged
        )
    )

    public_user_source_user = UserSourceUser(
        public_user_source, None, 1, "US public", "e@ma.il"
    )

    perm_manager = ElementVisibilityPermissionManager()
    checks = []
    for user in [
        public_user_source_user,
        AnonymousUser(),
    ]:
        for perm_type, scope in [
            (
                DispatchBuilderWorkflowActionOperationType.type,
                workflow_action_all,
            ),
            (
                DispatchBuilderWorkflowActionOperationType.type,
                workflow_action_logged_in,
            ),
            (
                DispatchBuilderWorkflowActionOperationType.type,
                workflow_action_not_logged,
            ),
        ]:
            checks.append(PermissionCheck(user, perm_type, scope))

    result = perm_manager.check_multiple_permissions(checks, builder.workspace)

    list_result = [
        (
            c.actor.username,
            c.operation_name,
            c.context.element.visibility,
            result.get(c, None),
        )
        for c in checks
    ]

    assert list_result == [
        (
            "US public",
            "builder.page.workflow_action.dispatch",
            Element.VISIBILITY_TYPES.ALL,
            None,
        ),
        (
            "US public",
            "builder.page.workflow_action.dispatch",
            Element.VISIBILITY_TYPES.LOGGED_IN,
            None,
        ),
        (
            "US public",
            "builder.page.workflow_action.dispatch",
            Element.VISIBILITY_TYPES.NOT_LOGGED,
            False,
        ),
        (
            "",
            "builder.page.workflow_action.dispatch",
            Element.VISIBILITY_TYPES.ALL,
            None,
        ),
        (
            "",
            "builder.page.workflow_action.dispatch",
            Element.VISIBILITY_TYPES.LOGGED_IN,
            False,
        ),
        (
            "",
            "builder.page.workflow_action.dispatch",
            Element.VISIBILITY_TYPES.NOT_LOGGED,
            None,
        ),
    ]


@pytest.mark.django_db
def test_element_visibility_permission_manager_filter_queryset(
    data_fixture,
    stub_user_source_registry,
):
    user = data_fixture.create_user(username="Auth user")
    builder = data_fixture.create_builder_application(user=user)
    builder_to = data_fixture.create_builder_application(workspace=None)
    domain1 = data_fixture.create_builder_custom_domain(
        builder=builder, published_to=builder_to
    )

    public_page = data_fixture.create_builder_page(builder=builder_to)

    public_user_source = data_fixture.create_user_source_with_first_type(
        application=builder_to
    )

    element_all = data_fixture.create_builder_button_element(
        page=public_page, visibility=Element.VISIBILITY_TYPES.ALL
    )

    element_logged_in = data_fixture.create_builder_button_element(
        page=public_page, visibility=Element.VISIBILITY_TYPES.LOGGED_IN
    )

    element_not_logged = data_fixture.create_builder_button_element(
        page=public_page, visibility=Element.VISIBILITY_TYPES.NOT_LOGGED
    )

    workflow_action_all = data_fixture.create_local_baserow_create_row_workflow_action(
        page=public_page, element=element_all
    )
    workflow_action_logged_in = (
        data_fixture.create_local_baserow_create_row_workflow_action(
            page=public_page, element=element_logged_in
        )
    )
    workflow_action_not_logged = (
        data_fixture.create_local_baserow_create_row_workflow_action(
            page=public_page, element=element_not_logged
        )
    )

    public_user_source_user = UserSourceUser(
        public_user_source, None, 1, "US public", "e@ma.il"
    )

    perm_manager = ElementVisibilityPermissionManager()

    ##
    # Element
    ##

    # Ensure that for an Editor user, all elements are returned.
    all_elements_for_auth = perm_manager.filter_queryset(
        user,
        ListElementsPageOperationType.type,
        Element.objects.all(),
    )
    assert len(all_elements_for_auth) == 3

    # Ensure that for an Authenticated UserSourceUser, the element with
    # visibility of NOT_LOGGED is excluded.
    all_elements_for_auth = perm_manager.filter_queryset(
        public_user_source_user,
        ListElementsPageOperationType.type,
        Element.objects.all(),
    )
    assert len(all_elements_for_auth) == 2
    assert all(
        [
            e.visibility != Element.VISIBILITY_TYPES.NOT_LOGGED
            for e in all_elements_for_auth
        ]
    )

    # Ensure that for an Anonymous user, only two elements are returned.
    # The third element with LOGGED_IN visibility should be excluded.
    all_elements_for_anonymous = perm_manager.filter_queryset(
        AnonymousUser(),
        ListElementsPageOperationType.type,
        Element.objects.all(),
    )
    assert len(all_elements_for_anonymous) == 2
    assert all(
        [
            e.visibility != Element.VISIBILITY_TYPES.LOGGED_IN
            for e in all_elements_for_anonymous
        ]
    )

    ##
    # Workflow actions
    ##

    # Ensure that for an Authenticated UserSourceUser, the element with
    # visibility of NOT_LOGGED is excluded.
    all_was_for_auth = perm_manager.filter_queryset(
        public_user_source_user,
        ListBuilderWorkflowActionsPageOperationType.type,
        BuilderWorkflowAction.objects.all(),
    )
    assert len(all_was_for_auth) == 2
    assert all(
        [
            wa.element.visibility != Element.VISIBILITY_TYPES.NOT_LOGGED
            for wa in all_was_for_auth
        ]
    )

    # Ensure that for an Anonymous user, only two elements are returned.
    # The third element with LOGGED_IN visibility should be excluded.
    all_was_for_anonymous = perm_manager.filter_queryset(
        AnonymousUser(),
        ListBuilderWorkflowActionsPageOperationType.type,
        BuilderWorkflowAction.objects.all(),
    )
    assert len(all_was_for_anonymous) == 2
    assert all(
        [
            wa.element.visibility != Element.VISIBILITY_TYPES.LOGGED_IN
            for wa in all_was_for_anonymous
        ]
    )


@pytest.fixture(autouse=True)
def ab_builder_user_page(data_fixture):
    """A fixture to help test Element permissions."""

    user = data_fixture.create_user()
    builder = data_fixture.create_builder_application(user=user)
    builder_to = data_fixture.create_builder_application(workspace=None)
    domain = data_fixture.create_builder_custom_domain(
        builder=builder, published_to=builder_to
    )
    public_page = data_fixture.create_builder_page(builder=builder_to)
    user_source = data_fixture.create_user_source_with_first_type(
        application=builder_to
    )
    return (user_source, builder, public_page)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role,roles,role_type,expected_check_result",
    [
        # The following tests set the role_type to ALLOW_ALL, which means that
        # the default behaviour is to allow access to the element for all
        # authenticated users.
        #
        # User's role is an empty string.
        (
            "",
            ["foo_role"],
            Element.ROLE_TYPES.ALLOW_ALL,
            None,
        ),
        # User's role is non-empty.
        (
            "foo_role",
            [],
            Element.ROLE_TYPES.ALLOW_ALL,
            None,
        ),
        # User's role does not match a value in roles. The check should still
        # pass because the role_type is ALLOW_ALL.
        (
            "foo_role",
            ["bar_role"],
            Element.ROLE_TYPES.ALLOW_ALL,
            None,
        ),
        # The following tests set the role_type to ALLOW_ALL_EXCEPT. This
        # means that if the user's role exists in the roles list, it should
        # cause the permission check to fail.
        #
        # User's role is an empty string.
        (
            "",
            ["foo_role"],
            Element.ROLE_TYPES.ALLOW_ALL_EXCEPT,
            None,
        ),
        # User's role doesn't match any excluded role (because roles is empty).
        # This check should therefore pass.
        (
            "foo_role",
            [],
            Element.ROLE_TYPES.ALLOW_ALL_EXCEPT,
            None,
        ),
        # User's role does not match the excluded roles. The check should
        # therefore pass.
        (
            "foo_role",
            ["bar_role"],
            Element.ROLE_TYPES.ALLOW_ALL_EXCEPT,
            None,
        ),
        # User's role matches an excluded roles. The check should therefore fail.
        (
            "foo_role",
            ["foo_role"],
            Element.ROLE_TYPES.ALLOW_ALL_EXCEPT,
            False,
        ),
        # The following tests set the role_type to DISALLOW_ALL_EXCEPT. This
        # means that the default behaviour is to disallow the user's role,
        # unless the role is in the roles list.
        #
        # User's role is an empty string. The check should fail because the
        # role (empty string) doesn't match an excluded role.
        (
            "",
            ["foo_role"],
            Element.ROLE_TYPES.DISALLOW_ALL_EXCEPT,
            False,
        ),
        # User's role doesn't match an excluded role (which is empty). This
        # check should therefore fail.
        (
            "foo_role",
            [],
            Element.ROLE_TYPES.DISALLOW_ALL_EXCEPT,
            False,
        ),
        # User's role does not match the excluded roles. The check should
        # therefore fail.
        (
            "foo_role",
            ["bar_role"],
            Element.ROLE_TYPES.DISALLOW_ALL_EXCEPT,
            False,
        ),
        # User's role matches an excluded roles. The check should therefore pass.
        (
            "foo_role",
            ["foo_role"],
            Element.ROLE_TYPES.DISALLOW_ALL_EXCEPT,
            None,
        ),
    ],
)
def test_permission_check_fails_if_logged_in_and_role_not_allowed(
    ab_builder_user_page,
    data_fixture,
    role,
    roles,
    role_type,
    expected_check_result,
):
    """
    If the user is authenticated but doesn't have a role, ensure the permission
    check fails if the element requires that role.

    expected_check_result should be one of:
        - False if the check failed (i.e. permission denied)
        - None if the check didn't get evaluated
    """

    public_user_source, builder, public_page = ab_builder_user_page

    # Create a user with the role
    public_user_source_user = UserSourceUser(
        public_user_source,
        None,
        1,
        "foo_username",
        "foo@bar.com",
        role,
    )

    # Create element that requires the role
    element = data_fixture.create_builder_button_element(
        page=public_page,
        visibility=Element.VISIBILITY_TYPES.LOGGED_IN,
        roles=roles,
        role_type=role_type,
    )

    # Create workflow action connected to the element that requires the role
    workflow_action_logged_in = (
        data_fixture.create_local_baserow_create_row_workflow_action(
            page=public_page, element=element
        )
    )

    perm_manager = ElementVisibilityPermissionManager()
    checks = []
    for user in [
        public_user_source_user,
        AnonymousUser(),
    ]:
        checks.append(
            PermissionCheck(
                user,
                DispatchBuilderWorkflowActionOperationType.type,
                workflow_action_logged_in,
            )
        )

    result = perm_manager.check_multiple_permissions(checks, builder.workspace)
    list_result = [
        (
            c.actor.username,
            c.operation_name,
            c.context.element.visibility,
            result.get(c, None),
        )
        for c in checks
    ]
    assert list_result == [
        (
            "foo_username",
            "builder.page.workflow_action.dispatch",
            Element.VISIBILITY_TYPES.LOGGED_IN,
            expected_check_result,
        ),
        (
            "",
            "builder.page.workflow_action.dispatch",
            Element.VISIBILITY_TYPES.LOGGED_IN,
            # Anon user should always cause a permission check failure
            False,
        ),
    ]


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role,roles,role_type,element_count",
    [
        # The following tests set the role_type to ALLOW_ALL, which means that
        # the default behaviour is to include the element in the queryset if
        # the user is authenticated.
        #
        # User's role is an empty string.
        (
            "",
            ["foo_role"],
            Element.ROLE_TYPES.ALLOW_ALL,
            1,
        ),
        # User has a role, but the roles list is empty.
        (
            "foo_role",
            [],
            Element.ROLE_TYPES.ALLOW_ALL,
            1,
        ),
        # User's role does not match roles list.
        (
            "foo_role",
            ["bar_role"],
            Element.ROLE_TYPES.ALLOW_ALL,
            1,
        ),
        # The following tests set the role_type to ALLOW_ALL_EXCEPT. This
        # means that the default behaviour is to include the element in the
        # queryset, unless the user's role is in the roles list.
        #
        # User's role is an empty string, which doesns't match the roles list.
        (
            "",
            ["foo_role"],
            Element.ROLE_TYPES.ALLOW_ALL_EXCEPT,
            1,
        ),
        # User's role doesn't match an excluded role (which is empty).
        (
            "foo_role",
            [],
            Element.ROLE_TYPES.ALLOW_ALL_EXCEPT,
            1,
        ),
        # User's role does not match the excluded roles.
        (
            "foo_role",
            ["bar_role"],
            Element.ROLE_TYPES.ALLOW_ALL_EXCEPT,
            1,
        ),
        # User's role matches an excluded role. The element should therefore
        # not be included in the queryset.
        (
            "foo_role",
            ["foo_role"],
            Element.ROLE_TYPES.ALLOW_ALL_EXCEPT,
            0,
        ),
        # The following tests set the role_type to DISALLOW_ALL_EXCEPT, which
        # means that the default behaviour is to exclude the element from
        # the queryset unless the user's role is in the roles list.
        #
        # User's role is an empty string.
        (
            "",
            ["foo_role"],
            Element.ROLE_TYPES.DISALLOW_ALL_EXCEPT,
            0,
        ),
        # User's role doesn't match any allowed roles (which is empty).
        (
            "foo_role",
            [],
            Element.ROLE_TYPES.DISALLOW_ALL_EXCEPT,
            0,
        ),
        # User's role does not match an allowed roles.
        (
            "foo_role",
            ["bar_role"],
            Element.ROLE_TYPES.DISALLOW_ALL_EXCEPT,
            0,
        ),
        # User's role matches an allowed roles. The element should therefore
        # be included in the queryset.
        (
            "foo_role",
            ["foo_role"],
            Element.ROLE_TYPES.DISALLOW_ALL_EXCEPT,
            1,
        ),
    ],
)
def test_queryset_only_includes_elements_allowed_by_role(
    ab_builder_user_page,
    data_fixture,
    role,
    roles,
    role_type,
    element_count,
):
    """
    Ensure that the queryset is correctly filtered against the element's
    allowed and disallowed roles and the user's role.

    If the element requires or forbids a role which the user's role matches,
    that element should not be in the returned queryset.
    """

    public_user_source, _, public_page = ab_builder_user_page

    public_user_source_user = UserSourceUser(
        public_user_source,
        None,
        1,
        "foo_username",
        "foo@bar.com",
        role,
    )

    # Create an element that requires the role
    element = data_fixture.create_builder_button_element(
        page=public_page,
        visibility=Element.VISIBILITY_TYPES.LOGGED_IN,
        roles=roles,
        role_type=role_type,
    )

    # Create a workflow action connected to the element that requires the role
    workflow_action_logged_in = (
        data_fixture.create_local_baserow_create_row_workflow_action(
            page=public_page, element=element
        )
    )

    perm_manager = ElementVisibilityPermissionManager()

    for operation_type in [
        ListBuilderWorkflowActionsPageOperationType.type,
        ListElementsPageOperationType.type,
    ]:
        elements = perm_manager.filter_queryset(
            public_user_source_user,
            ListElementsPageOperationType.type,
            Element.objects.all(),
        )

        assert len(elements) == element_count


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role,roles,role_type,expected_bool_result",
    [
        # If the role_type is 'allow_all', then it should always return True
        (
            "",
            [],
            Element.ROLE_TYPES.ALLOW_ALL,
            True,
        ),
        (
            "",
            ["foo_role"],
            Element.ROLE_TYPES.ALLOW_ALL,
            True,
        ),
        (
            "bar_role",
            ["foo_role"],
            Element.ROLE_TYPES.ALLOW_ALL,
            True,
        ),
        (
            "foo_role",
            ["foo_role"],
            Element.ROLE_TYPES.ALLOW_ALL,
            True,
        ),
        # If the role_type is 'allow_all_except', ensure True is returned
        # only if the user's role is *not* in the roles list.
        (
            "",
            [],
            Element.ROLE_TYPES.ALLOW_ALL_EXCEPT,
            True,
        ),
        (
            "",
            ["foo_role"],
            Element.ROLE_TYPES.ALLOW_ALL_EXCEPT,
            True,
        ),
        (
            "bar_role",
            ["foo_role"],
            Element.ROLE_TYPES.ALLOW_ALL_EXCEPT,
            True,
        ),
        # Should return False, since foo_role is disallowed.
        (
            "foo_role",
            ["foo_role"],
            Element.ROLE_TYPES.ALLOW_ALL_EXCEPT,
            False,
        ),
        # If the role_type is 'disallow_all_except', ensure True is returned
        # *only* if the user's role is in the roles list.
        (
            "",
            [],
            Element.ROLE_TYPES.DISALLOW_ALL_EXCEPT,
            False,
        ),
        (
            "",
            ["foo_role"],
            Element.ROLE_TYPES.DISALLOW_ALL_EXCEPT,
            False,
        ),
        (
            "bar_role",
            ["foo_role"],
            Element.ROLE_TYPES.DISALLOW_ALL_EXCEPT,
            False,
        ),
        # Should return True, since foo_role is allowed.
        (
            "foo_role",
            ["foo_role"],
            Element.ROLE_TYPES.DISALLOW_ALL_EXCEPT,
            True,
        ),
        # If its a UserSourceUser and a permission isn't explictly granted,
        # ensure False is returned for safety.
        (
            "foo_role",
            ["foo_role"],
            "invalid_role_type",
            False,
        ),
    ],
)
def test_auth_user_can_view_element_returns_expected_bool(
    ab_builder_user_page,
    data_fixture,
    role,
    roles,
    role_type,
    expected_bool_result,
):
    """
    Test the auth_user_can_view_element(). Ensure the correct True or False bool
    is returned, depending on the user object and the element.
    """

    public_user_source, _, public_page = ab_builder_user_page

    # Create a user with a role
    user_source_user = UserSourceUser(
        public_user_source,
        None,
        1,
        "foo_username",
        "foo@bar.com",
        role,
    )

    # Create an element with a role and role_type
    element = data_fixture.create_builder_button_element(
        page=public_page,
        # The visibility value doesn't really matter for testing this method
        visibility=Element.VISIBILITY_TYPES.LOGGED_IN,
        roles=roles,
        role_type=role_type,
    )
    perm_manager = ElementVisibilityPermissionManager()

    result = perm_manager.auth_user_can_view_element(user_source_user, element)

    assert result is expected_bool_result


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role,expected_role",
    [
        ("foo_role", "foo_role"),
        ("bar_role", "bar_role"),
        ("", ""),
        ("  ", "  "),
    ],
)
def test_get_roles_returns_role(
    ab_builder_user_page,
    role,
    expected_role,
):
    """
    Test the UserSourceUser::get_role() method. Ensure the expected
    role is returned.
    """

    public_user_source, _, _ = ab_builder_user_page

    user_source_user = UserSourceUser(
        public_user_source,
        None,
        1,
        "foo_username",
        "foo@bar.com",
        role,
    )

    assert user_source_user.get_role() == expected_role


@pytest.mark.parametrize(
    "role,roles,role_type",
    [
        (
            "foo_role",
            ["foo_role"],
            Element.ROLE_TYPES.ALLOW_ALL,
        ),
        (
            "foo_role",
            [],
            Element.ROLE_TYPES.ALLOW_ALL_EXCEPT,
        ),
        (
            "foo_role",
            ["foo_role"],
            Element.ROLE_TYPES.DISALLOW_ALL_EXCEPT,
        ),
    ],
)
@pytest.mark.django_db
def test_auth_user_can_view_element_returns_true(
    ab_builder_user_page,
    data_fixture,
    role,
    roles,
    role_type,
):
    """
    Test the auth_user_can_view_element(). Ensure that if the visibility is LOGGED_IN
    and the user type is UserSourceUser, then True should always be returned.
    """

    public_user_source, _, public_page = ab_builder_user_page

    # Create an element with a role and role_type
    element = data_fixture.create_builder_button_element(
        page=public_page,
        # The visibility value doesn't really matter for testing this method
        visibility=Element.VISIBILITY_TYPES.LOGGED_IN,
        roles=roles,
        role_type=role_type,
    )
    perm_manager = ElementVisibilityPermissionManager()

    user_source_user = UserSourceUser(
        public_user_source,
        None,
        1,
        "foo_username",
        "foo@bar.com",
        role,
    )

    result = perm_manager.auth_user_can_view_element(user_source_user, element)

    assert result is True


@pytest.mark.django_db
def test_auth_user_can_view_element_returns_true_if_role_type_is_none(
    ab_builder_user_page,
    data_fixture,
):
    """
    Test the auth_user_can_view_element(). Ensure that if the role_type is None, it
    is treated the same as the default, which is ALLOW_ALL.

    This is a temporary solution to support zero downtime. This should be
    removed in an upcoming release.

    See: https://gitlab.com/baserow/baserow/-/issues/2724
    """

    _, _, public_page = ab_builder_user_page

    # Create an element with a role and role_type
    element = data_fixture.create_builder_button_element(
        page=public_page,
        # The visibility value doesn't really matter for testing this method
        visibility=Element.VISIBILITY_TYPES.LOGGED_IN,
        roles=[],
        role_type=None,
    )
    perm_manager = ElementVisibilityPermissionManager()

    result = perm_manager.auth_user_can_view_element(AnonymousUser(), element)

    assert result is True
