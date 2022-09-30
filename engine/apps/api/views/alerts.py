from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.alerts.models import Alert
from apps.api.permissions import RBACPermission
from apps.api.serializers.alert import AlertRawSerializer
from apps.auth_token.auth import PluginAuthentication


class AlertDetailView(APIView):
    authentication_classes = [PluginAuthentication]
    permission_classes = [IsAuthenticated, RBACPermission]

    rbac_permissions = {
        "get": [RBACPermission.Permissions.ALERT_GROUPS_READ],
    }

    def get(self, request, id):
        try:
            alert = Alert.objects.get(public_primary_key=id)
        except Alert.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if alert.group.channel.organization != request.auth.organization:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = AlertRawSerializer(alert)
        return Response(serializer.data)
