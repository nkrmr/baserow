from rest_framework import serializers

from baserow.api.user_files.serializers import UserFileField
from baserow.core.models import Settings


class SettingsSerializer(serializers.ModelSerializer):
    allow_global_group_creation = serializers.BooleanField(
        required=False,
        source="allow_global_workspace_creation",
        help_text="DEPRECATED: Please use the functionally identical "
        "`allow_global_workspace_creation` instead as this attribute is "
        "being removed in the future.",
    )  # GroupDeprecation
    allow_signups_via_group_invitations = serializers.BooleanField(
        required=False,
        source="allow_signups_via_workspace_invitations",
        help_text="DEPRECATED: Please use the functionally identical "
        "`allow_signups_via_workspace_invitations` instead as this attribute "
        "is being removed in the future.",
    )  # GroupDeprecation
    co_branding_logo = UserFileField(
        required=False,
        help_text="Co-branding logo that's placed next to the Baserow logo (176x29).",
    )

    class Meta:
        model = Settings
        fields = (
            "allow_new_signups",
            "allow_signups_via_workspace_invitations",
            "allow_signups_via_group_invitations",  # GroupDeprecation
            "allow_reset_password",
            "allow_global_workspace_creation",
            "allow_global_group_creation",  # GroupDeprecation
            "account_deletion_grace_delay",
            "show_admin_signup_page",
            "track_workspace_usage",
            "show_baserow_help_request",
            "co_branding_logo",
            "email_verification",
        )
        extra_kwargs = {
            "allow_new_signups": {"required": False},
            "allow_signups_via_workspace_invitations": {"required": False},
            "allow_reset_password": {"required": False},
            "allow_global_workspace_creation": {"required": False},
            "account_deletion_grace_delay": {"required": False},
            "track_workspace_usage": {"required": False},
            "show_baserow_help_request": {"required": False},
            "email_verification": {"required": False},
        }

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        # TODO Remove in a future release once email_verification is null=False
        if representation["email_verification"] is None:
            representation[
                "email_verification"
            ] = Settings.EmailVerificationOptions.NO_VERIFICATION

        return representation

    def to_internal_value(self, data):
        # TODO Remove in a future release once email_verification is null=False
        if "email_verification" in data and data["email_verification"] is None:
            raise serializers.ValidationError(
                detail={"email_verification": ["'null' is not a valid choice."]},
                code="invalid_choice",
            )

        return super().to_internal_value(data)


class InstanceIdSerializer(serializers.ModelSerializer):
    class Meta:
        model = Settings
        fields = ("instance_id",)
        extra_kwargs = {
            "instance_id": {"read_only": True},
        }
