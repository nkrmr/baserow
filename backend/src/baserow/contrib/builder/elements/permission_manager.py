from django.contrib.auth import get_user_model
from django.db.models import Q

from baserow.contrib.builder.elements.operations import ListElementsPageOperationType
from baserow.contrib.builder.workflow_actions.operations import (
    DispatchBuilderWorkflowActionOperationType,
    ListBuilderWorkflowActionsPageOperationType,
)
from baserow.core.registries import PermissionManagerType
from baserow.core.subjects import AnonymousUserSubjectType, UserSubjectType
from baserow.core.user_sources.subjects import UserSourceUserSubjectType

from .models import Element

User = get_user_model()


class ElementVisibilityPermissionManager(PermissionManagerType):
    """This permission manager handle the element visibility permissions."""

    type = "element_visibility"
    supported_actor_types = [
        UserSourceUserSubjectType.type,
        UserSubjectType.type,
        AnonymousUserSubjectType.type,
    ]

    def auth_user_can_view_element(self, user, element):
        """
        Note: This method is currently only used by `check_multiple_permissions()`
        to check the user's permissions when dispatching a workflow action.

        Return True if the user should be allowed to view the element.
        Otherwise return False. The user type, user's role, and element's
        role_type are evaluated together to determine if the user should be
        allowed to view the element.

        Otherwise, the user's role and element's role_type are further evaluated.
            - If the role_type is 'allow_all', any user is allowed to view
                the element.
            - If the role_type is 'allow_all_except', any user is allowed
                to view the element, except for those users whose role is
                in the element's roles list.
            - If the role_type is 'disallow_all_except', all users are
                disallowed from viewing the element, unless the user's role
                is in the element's roles list.
        """

        # If the user type is `User` (e.g. Editor user), it won't have a role
        # or role_type. In which case, return True by default so that the
        # elements can be viewed in the editor.
        if isinstance(user, User):
            return True

        # TODO: This is to support zero-downtime migration. This will be
        #   removed in the next release.
        #   See: https://gitlab.com/baserow/baserow/-/issues/2724
        if element.role_type is None:
            return True

        if element.role_type == Element.ROLE_TYPES.ALLOW_ALL:
            return True
        elif element.role_type == Element.ROLE_TYPES.ALLOW_ALL_EXCEPT:
            # Check if the user's role is disallowed
            return user.role not in element.roles
        elif element.role_type == Element.ROLE_TYPES.DISALLOW_ALL_EXCEPT:
            # Check if the user's role is allowed
            return user.role in element.roles

        # Return False by default for safety
        return False

    def check_multiple_permissions(
        self,
        checks,
        workspace=None,
        include_trash=False,
    ):
        """
        If an element is not visible it should be impossible to dispatch an action
        related to this element.
        """

        result = {}

        for check in checks:
            if check.operation_name == DispatchBuilderWorkflowActionOperationType.type:
                if getattr(check.actor, "is_authenticated", False):
                    if (
                        check.context.element.visibility
                        == Element.VISIBILITY_TYPES.NOT_LOGGED
                    ):
                        result[check] = False
                    elif not self.auth_user_can_view_element(
                        check.actor, check.context.element
                    ):
                        result[check] = False
                else:
                    if (
                        check.context.element.visibility
                        == Element.VISIBILITY_TYPES.LOGGED_IN
                    ):
                        result[check] = False

        return result

    def filter_queryset(
        self,
        actor,
        operation_name: str,
        queryset,
        workspace=None,
    ):
        """Filters out invisible elements and their workflow actions."""

        if isinstance(actor, User):
            return queryset

        if operation_name == ListElementsPageOperationType.type:
            if getattr(actor, "is_authenticated", False):
                queryset = (
                    queryset.exclude(visibility=Element.VISIBILITY_TYPES.NOT_LOGGED)
                    .exclude(
                        Q(role_type=Element.ROLE_TYPES.ALLOW_ALL_EXCEPT)
                        & Q(roles__contains=actor.role)
                    )
                    .exclude(
                        Q(role_type=Element.ROLE_TYPES.DISALLOW_ALL_EXCEPT)
                        & ~Q(roles__contains=actor.role)
                    )
                )
                return queryset
            else:
                return queryset.exclude(visibility=Element.VISIBILITY_TYPES.LOGGED_IN)

        elif operation_name == ListBuilderWorkflowActionsPageOperationType.type:
            if getattr(actor, "is_authenticated", False):
                queryset = (
                    queryset.exclude(
                        element__visibility=Element.VISIBILITY_TYPES.NOT_LOGGED
                    )
                    .exclude(
                        Q(element__role_type=Element.ROLE_TYPES.ALLOW_ALL_EXCEPT)
                        & Q(element__roles__contains=actor.role)
                    )
                    .exclude(
                        Q(element__role_type=Element.ROLE_TYPES.DISALLOW_ALL_EXCEPT)
                        & ~Q(element__roles__contains=actor.role)
                    )
                )
                return queryset
            else:
                return queryset.exclude(
                    element__visibility=Element.VISIBILITY_TYPES.LOGGED_IN
                )

        return queryset
