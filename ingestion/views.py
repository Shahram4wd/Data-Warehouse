from django.shortcuts import render
from rest_framework import views, status
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from django.conf import settings

from .serializers import UserSyncSerializer
from ingestion.genius.genius_client import GeniusClient
from ingestion.genius.user_sync import UserSync  # Updated import

class GeniusUserSyncView(views.APIView):
    serializer_class = UserSyncSerializer
    
    @extend_schema(
        summary="Sync users from Genius API",
        description="Syncs user data from the Genius API into the Data Warehouse. "
                   "Syncs a single user if user_id is provided, otherwise syncs all users.",
        parameters=[
            OpenApiParameter(
                name="user_id", 
                description="ID of a specific user to sync", 
                required=False, 
                type=int
            ),
        ],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "message": {"type": "string"},
                    "data": {
                        "type": "object",
                        "properties": {
                            "total_synced": {"type": "integer", "nullable": True},
                            "user_id": {"type": "integer", "nullable": True}
                        }
                    }
                }
            },
            400: {"description": "Bad request"},
            500: {"description": "Internal server error"}
        },
        examples=[
            OpenApiExample(
                "Sync All Users",
                value={"success": True, "message": "All users sync complete", "data": {"total_synced": 125, "user_id": None}},
                request_only=False,
                response_only=True,
            ),
            OpenApiExample(
                "Sync Single User",
                value={"success": True, "message": "User synced successfully", "data": {"total_synced": 1, "user_id": 42}},
                request_only=False,
                response_only=True,
            ),
        ],
    )
    def post(self, request, format=None):
        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"success": False, "message": "Invalid input", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            client = GeniusClient(
                settings.GENIUS_API_URL,
                settings.GENIUS_USERNAME,
                settings.GENIUS_PASSWORD
            )
            
            user_id = serializer.validated_data.get('user_id')
            sync = UserSync(client)  # Create instance of UserSync
            
            if user_id:
                # Sync single user
                result_id = sync.sync_single(user_id)
                return Response({
                    "success": True,
                    "message": f"User synced successfully",
                    "data": {"user_id": result_id, "total_synced": 1}
                })
            else:
                # Sync all users
                total_synced = sync.sync_all()
                return Response({
                    "success": True,
                    "message": "All users sync complete",
                    "data": {"total_synced": total_synced, "user_id": None}
                })
                
        except Exception as e:
            return Response(
                {"success": False, "message": f"Failed to sync: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
