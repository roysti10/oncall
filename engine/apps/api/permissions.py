import enum
import typing

from rest_framework import permissions
from rest_framework.request import Request
from rest_framework.views import APIView
from rest_framework.viewsets import ViewSet


class Resources(enum.Enum):
    ALERT_GROUPS = "alert-groups"
    ALERT_RECEIVE_CHANNELS = "alert-receive-channels"
    INTEGRATIONS = "integrations"
    ESCALATION_CHAINS = "escalation-chains"
    SCHEDULES = "schedules"
    CHATOPS = "chatops"
    OUTGOING_WEBHOOKS = "outgoing-webhooks"
    MAINTENANCE = "maintenance"
    API_KEYS = "api-keys"
    ONCALL_SHIFTS = "oncall-shifts"

    NOTIFICATION_SETTINGS = "notification-settings"
    GLOBAL_SETTINGS = "global-settings"
    OWN_SETTINGS = "own-settings"
    OTHERS_SETTINGS = "others-settings"

    # These are not oncall specific
    ORGANIZATIONS = "orgs"
    TEAMS = "teams"
    USERS = "users"


class Actions(enum.Enum):
    READ = "read"
    WRITE = "write"


def _generate_permission_string(resource: Resources, action: Actions, ignore_prefix=False) -> str:
    return f"{'' if ignore_prefix else 'grafana-oncall-app.'}{resource.value}:{action.value}"


class RBACPermission(permissions.BasePermission):
    class Permissions(enum.Enum):
        ALERT_GROUPS_READ = _generate_permission_string(Resources.ALERT_GROUPS, Actions.READ)
        ALERT_GROUPS_WRITE = _generate_permission_string(Resources.ALERT_GROUPS, Actions.WRITE)

        ALERT_RECEIVE_CHANNELS_READ = _generate_permission_string(Resources.ALERT_RECEIVE_CHANNELS, Actions.READ)
        ALERT_RECEIVE_CHANNELS_WRITE = _generate_permission_string(Resources.ALERT_RECEIVE_CHANNELS, Actions.WRITE)

        INTEGRATIONS_READ = _generate_permission_string(Resources.INTEGRATIONS, Actions.READ)
        INTEGRATIONS_WRITE = _generate_permission_string(Resources.INTEGRATIONS, Actions.WRITE)

        ESCALATION_CHAINS_READ = _generate_permission_string(Resources.ESCALATION_CHAINS, Actions.READ)
        ESCALATION_CHAINS_WRITE = _generate_permission_string(Resources.ESCALATION_CHAINS, Actions.WRITE)

        SCHEDULES_READ = _generate_permission_string(Resources.SCHEDULES, Actions.READ)
        SCHEDULES_WRITE = _generate_permission_string(Resources.SCHEDULES, Actions.WRITE)

        CHATOPS_READ = _generate_permission_string(Resources.CHATOPS, Actions.READ)
        CHATOPS_WRITE = _generate_permission_string(Resources.CHATOPS, Actions.WRITE)

        OUTGOING_WEBHOOKS_READ = _generate_permission_string(Resources.OUTGOING_WEBHOOKS, Actions.READ)
        OUTGOING_WEBHOOKS_WRITE = _generate_permission_string(Resources.OUTGOING_WEBHOOKS, Actions.WRITE)

        MAINTENANCE_READ = _generate_permission_string(Resources.MAINTENANCE, Actions.READ)
        MAINTENANCE_WRITE = _generate_permission_string(Resources.MAINTENANCE, Actions.WRITE)

        API_KEYS_READ = _generate_permission_string(Resources.API_KEYS, Actions.READ)
        API_KEYS_WRITE = _generate_permission_string(Resources.API_KEYS, Actions.WRITE)

        ONCALL_SHIFTS_READ = _generate_permission_string(Resources.ONCALL_SHIFTS, Actions.READ)
        ONCALL_SHIFTS_WRITE = _generate_permission_string(Resources.ONCALL_SHIFTS, Actions.WRITE)

        NOTIFICATION_SETTINGS_READ = _generate_permission_string(Resources.NOTIFICATION_SETTINGS, Actions.READ)
        NOTIFICATION_SETTINGS_WRITE = _generate_permission_string(Resources.NOTIFICATION_SETTINGS, Actions.WRITE)

        GLOBAL_SETTINGS_READ = _generate_permission_string(Resources.GLOBAL_SETTINGS, Actions.READ)
        GLOBAL_SETTINGS_WRITE = _generate_permission_string(Resources.GLOBAL_SETTINGS, Actions.WRITE)

        OWN_SETTINGS_READ = _generate_permission_string(Resources.OWN_SETTINGS, Actions.READ)
        OWN_SETTINGS_WRITE = _generate_permission_string(Resources.OWN_SETTINGS, Actions.WRITE)

        OTHERS_SETTINGS_READ = _generate_permission_string(Resources.OTHERS_SETTINGS, Actions.READ)
        OTHERS_SETTINGS_WRITE = _generate_permission_string(Resources.OTHERS_SETTINGS, Actions.WRITE)

        ORGANIZATIONS_READ = _generate_permission_string(Resources.ORGANIZATIONS, Actions.READ, True)
        TEAMS_READ = _generate_permission_string(Resources.TEAMS, Actions.READ, True)
        USERS_READ = _generate_permission_string(Resources.USERS, Actions.READ, True)

    def has_permission(self, request: Request, view: typing.Union[ViewSet, APIView]) -> bool:
        from apps.grafana_plugin.helpers.client import GrafanaAPIClient

        # TODO: figure out caching strategy...

        user = request.user

        if not user:
            return False

        organization = user.organization
        user_id = user.user_id

        # For right now this needs to support being used in both a ViewSet as well as
        # APIView, we use both interchangably
        action = view.action if isinstance(view, ViewSet) else request.method
        rbac_permissions: typing.Dict[str, typing.List[RBACPermission.Permissions]] = getattr(
            view, "rbac_permissions", None
        )

        assert (
            rbac_permissions is not None
        ), "Must define a `rbac_permissions` dict on the ViewSet that is consuming the RBACPermission class"

        user_has_all_required_permissions = True
        grafana_client = GrafanaAPIClient(api_url=organization.grafana_url, api_token=organization.api_token)

        for required_permission in rbac_permissions.get(action, []):
            user_has_all_required_permissions = grafana_client.user_has_permission(user_id, required_permission)
        return user_has_all_required_permissions

    # TODO:
    # def has_object_permission(self, request: Request, view: ViewSet, obj: Any) -> bool:
    #     # action_object_permissions attr should be used in case permission check require lookup
    #     # for some object's properties e.g. team.
    #     if getattr(view, "action_object_permissions", None):
    #         for permission, actions in getattr(view, "action_object_permissions", {}).items():
    #             if view.action in actions:
    #                 return permission().has_object_permission(request, view, obj)
    #         return False
    #     else:
    #         # has_object_permission is called after has_permission, so return True if in view there is not
    #         # action_object_permission attr which mean no additional check involving object required
    #         return True
