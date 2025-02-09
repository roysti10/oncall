import typing

from rest_framework import serializers

from apps.alerts.models import AlertReceiveChannel, ChannelFilter, EscalationChain
from apps.api.serializers.labels import LabelPairSerializer
from apps.base.messaging import get_messaging_backend_from_id
from apps.telegram.models import TelegramToOrganizationConnector
from common.api_helpers.custom_fields import OrganizationFilteredPrimaryKeyRelatedField
from common.api_helpers.exceptions import BadRequest
from common.api_helpers.mixins import EagerLoadingMixin
from common.api_helpers.utils import valid_jinja_template_for_serializer_method_field
from common.jinja_templater.apply_jinja_template import JinjaTemplateError
from common.utils import is_regex_valid


class SlackChannelDetails(typing.TypedDict):
    display_name: str
    slack_id: str
    id: str


class ChannelFilterSerializer(EagerLoadingMixin, serializers.ModelSerializer):
    class TelegramChannelDetailsSerializer(serializers.Serializer):
        display_name = serializers.CharField(source="channel_name")
        id = serializers.CharField(source="channel_chat_id")

    id = serializers.CharField(read_only=True, source="public_primary_key")
    alert_receive_channel = OrganizationFilteredPrimaryKeyRelatedField(queryset=AlertReceiveChannel.objects)
    escalation_chain = OrganizationFilteredPrimaryKeyRelatedField(
        queryset=EscalationChain.objects,
        filter_field="organization",
        allow_null=True,
        required=False,
    )
    slack_channel = serializers.SerializerMethodField()
    # Duplicated telegram channel and telegram_channel_details field for backwards compatibility for old integration page
    telegram_channel = OrganizationFilteredPrimaryKeyRelatedField(
        queryset=TelegramToOrganizationConnector.objects, filter_field="organization", allow_null=True, required=False
    )
    telegram_channel_details = TelegramChannelDetailsSerializer(
        source="telegram_channel", read_only=True, allow_null=True
    )
    filtering_term_as_jinja2 = serializers.SerializerMethodField()
    filtering_term = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    filtering_labels = LabelPairSerializer(many=True, required=False)

    SELECT_RELATED = ["escalation_chain", "alert_receive_channel"]

    class Meta:
        model = ChannelFilter
        fields = [
            "id",
            "alert_receive_channel",
            "escalation_chain",
            "slack_channel",
            "created_at",
            "filtering_labels",
            "filtering_term",
            "filtering_term_type",
            "telegram_channel",
            "is_default",
            "notify_in_slack",
            "notify_in_telegram",
            "notification_backends",
            "filtering_term_as_jinja2",
            "telegram_channel_details",
        ]
        read_only_fields = [
            "created_at",
            "is_default",
            "telegram_channel_details",
        ]

    def validate(self, data):
        filtering_term = data.get("filtering_term")
        filtering_term_type = data.get("filtering_term_type")
        if filtering_term is not None:
            if len(filtering_term) > ChannelFilter.FILTERING_TERM_MAX_LENGTH:
                raise serializers.ValidationError(
                    f"Expression is too long. Maximum length: {ChannelFilter.FILTERING_TERM_MAX_LENGTH} characters, "
                    f"current length: {len(filtering_term)}"
                )
        if filtering_term_type == ChannelFilter.FILTERING_TERM_TYPE_JINJA2:
            try:
                valid_jinja_template_for_serializer_method_field({"route_template": filtering_term})
            except JinjaTemplateError:
                raise serializers.ValidationError(["Jinja template is incorrect"])
        elif filtering_term_type == ChannelFilter.FILTERING_TERM_TYPE_REGEX or filtering_term_type is None:
            if filtering_term is not None:
                if not is_regex_valid(filtering_term):
                    raise serializers.ValidationError(["Regular expression is incorrect"])
        elif filtering_term_type == ChannelFilter.FILTERING_TERM_TYPE_LABELS:
            filtering_labels = data.get("filtering_labels")
            if filtering_labels is None:
                raise serializers.ValidationError(["Filtering labels field is required"])
        else:
            raise serializers.ValidationError(["Expression type is incorrect"])
        return data

    def get_slack_channel(self, obj) -> SlackChannelDetails | None:
        if obj.slack_channel_id is None:
            return None
        # display_name and id appears via annotate in ChannelFilterView.get_queryset()
        return {
            "display_name": obj.slack_channel_name,
            "slack_id": obj.slack_channel_id,
            "id": obj.slack_channel_pk,
        }

    def validate_slack_channel(self, slack_channel_id):
        from apps.slack.models import SlackChannel

        if slack_channel_id is not None:
            slack_channel_id = slack_channel_id.upper()
            organization = self.context["request"].auth.organization
            try:
                organization.slack_team_identity.get_cached_channels().get(slack_id=slack_channel_id)
            except SlackChannel.DoesNotExist:
                raise serializers.ValidationError(["Slack channel does not exist"])
        return slack_channel_id

    def validate_notification_backends(self, notification_backends):
        # NOTE: updates the whole field, handling dict updates per backend
        if notification_backends is not None:
            organization = self.context["request"].auth.organization
            if not isinstance(notification_backends, dict):
                raise serializers.ValidationError(["Invalid messaging backend data"])
            updated = self.instance.notification_backends or {}
            for backend_id in notification_backends:
                backend = get_messaging_backend_from_id(backend_id)
                if backend is None:
                    raise serializers.ValidationError(["Invalid messaging backend"])
                updated_data = backend.validate_channel_filter_data(
                    organization,
                    notification_backends[backend_id],
                )
                # update existing backend data
                updated[backend_id] = updated.get(backend_id, {}) | updated_data
            notification_backends = updated
        return notification_backends

    def get_filtering_term_as_jinja2(self, obj):
        """Returns the regex or labels filtering term as a jinja2, for preview purposes."""
        if obj.filtering_term_type == ChannelFilter.FILTERING_TERM_TYPE_JINJA2:
            return obj.filtering_term
        elif obj.filtering_term_type == ChannelFilter.FILTERING_TERM_TYPE_REGEX:
            # Four curly braces will result in two curly braces in the final string
            # rf"..." is a raw f string, to keep original filtering_term
            escaped_quotes = obj.filtering_term.replace('"', '\\"') if obj.filtering_term else ""
            return rf'{{{{ payload | json_dumps | regex_search("{escaped_quotes}") }}}}'
        elif obj.filtering_labels and obj.filtering_term_type == ChannelFilter.FILTERING_TERM_TYPE_LABELS:
            # required labels
            labels = [
                f"labels.{item['key']['name']} and labels.{item['key']['name']} == '{item['value']['name']}'"
                for item in obj.filtering_labels
            ]
            template = "{{{{ {conditions} }}}}".format(conditions=" and ".join(labels))
            return template


class ChannelFilterCreateSerializer(ChannelFilterSerializer):
    alert_receive_channel = OrganizationFilteredPrimaryKeyRelatedField(queryset=AlertReceiveChannel.objects)
    slack_channel = serializers.CharField(allow_null=True, required=False, source="slack_channel_id")

    class Meta:
        model = ChannelFilter
        fields = [
            "id",
            "alert_receive_channel",
            "escalation_chain",
            "slack_channel",
            "created_at",
            "filtering_labels",
            "filtering_term",
            "filtering_term_type",
            "telegram_channel",
            "is_default",
            "notify_in_slack",
            "notify_in_telegram",
            "notification_backends",
        ]
        read_only_fields = ["created_at", "is_default"]

    def _get_slack_channel(self, obj) -> SlackChannelDetails | None:
        if obj.slack_channel_id is None:
            return None
        slack_team_identity = self.context["request"].auth.organization.slack_team_identity
        if slack_team_identity is None:
            return None
        slack_channel = slack_team_identity.get_cached_channels(slack_id=obj.slack_channel_id).first()
        if slack_channel is None:
            return None
        return {
            "display_name": slack_channel.name,
            "slack_id": slack_channel.slack_id,
            "id": slack_channel.public_primary_key,
        }

    def to_representation(self, obj):
        """add correct slack channel data to result after instance creation/update"""
        result = super().to_representation(obj)
        result["slack_channel"] = self._get_slack_channel(obj)
        return result

    def create(self, validated_data):
        instance = super().create(validated_data)
        instance.to_index(0)  # the new route should be the first one
        return instance


class ChannelFilterUpdateSerializer(ChannelFilterCreateSerializer):
    alert_receive_channel = OrganizationFilteredPrimaryKeyRelatedField(read_only=True)

    class Meta(ChannelFilterCreateSerializer.Meta):
        read_only_fields = [*ChannelFilterCreateSerializer.Meta.read_only_fields, "alert_receive_channel"]
        extra_kwargs = {"filtering_term": {"required": False}}

    def update(self, instance, validated_data):
        filtering_term = validated_data.get("filtering_term")
        if instance.is_default and filtering_term is not None:
            raise BadRequest(detail="Filtering term of default channel filter cannot be changed")

        return super().update(instance, validated_data)


class ChannelFilterUpdateResponseSerializer(ChannelFilterUpdateSerializer):
    """
    This serializer is used in OpenAPI schema to show proper response structure,
    as `slack_channel` field expects string on create/update and returns dict on response
    """

    slack_channel = serializers.SerializerMethodField()

    def get_slack_channel(self, obj) -> SlackChannelDetails | None:
        return self._get_slack_channel(obj)
