from rest_framework import serializers

class UserSyncSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(required=False, help_text="Optional: The ID of a specific user to sync")