from django.shortcuts import render
from rest_framework import views, status
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from django.conf import settings
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache
import time
import logging

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

class DatabaseTestView(views.APIView):
    """Test database connectivity and performance"""
    
    @extend_schema(
        summary="Test database connection",
        description="Tests database connectivity, query performance, and displays connection info",
        responses={
            200: {
                "type": "object",
                "properties": {
                    "status": {"type": "string"},
                    "database_info": {"type": "object"},
                    "connection_test": {"type": "object"},
                    "query_test": {"type": "object"},
                    "cache_test": {"type": "object"}
                }
            }
        }
    )
    def get(self, request):
        """Test database connection and return detailed diagnostics"""
        results = {
            "status": "testing",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "database_info": {},
            "connection_test": {},
            "query_test": {},
            "cache_test": {}
        }
        
        # Test 1: Database Info
        try:
            db_settings = settings.DATABASES['default']
            results["database_info"] = {
                "engine": db_settings.get('ENGINE', 'unknown'),
                "name": db_settings.get('NAME', 'unknown'),
                "host": db_settings.get('HOST', 'unknown'),
                "port": db_settings.get('PORT', 'unknown'),
                "conn_max_age": db_settings.get('CONN_MAX_AGE', 'unknown'),
                "options": db_settings.get('OPTIONS', {}),
                "status": "success"
            }
        except Exception as e:
            results["database_info"] = {
                "status": "error",
                "error": str(e)
            }
        
        # Test 2: Basic Connection Test
        try:
            start_time = time.time()
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
            
            connection_time = (time.time() - start_time) * 1000
            
            results["connection_test"] = {
                "status": "success",
                "result": result[0] if result else None,
                "connection_time_ms": round(connection_time, 2),
                "connection_queries": len(connection.queries)
            }
        except Exception as e:
            results["connection_test"] = {
                "status": "error",
                "error": str(e),
                "error_type": type(e).__name__
            }
        
        # Test 3: Query Performance Test
        try:
            start_time = time.time()
            with connection.cursor() as cursor:
                # Test a simple query to an existing table
                cursor.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    LIMIT 5
                """)
                tables = cursor.fetchall()
            
            query_time = (time.time() - start_time) * 1000
            
            results["query_test"] = {
                "status": "success",
                "tables_found": len(tables),
                "sample_tables": [table[0] for table in tables[:3]],
                "query_time_ms": round(query_time, 2)
            }
        except Exception as e:
            results["query_test"] = {
                "status": "error",
                "error": str(e),
                "error_type": type(e).__name__
            }
        
        # Test 4: Cache Test
        try:
            test_key = "db_test_cache_key"
            test_value = f"test_value_{int(time.time())}"
            
            # Set cache
            cache.set(test_key, test_value, 60)
            
            # Get cache
            cached_value = cache.get(test_key)
            
            results["cache_test"] = {
                "status": "success",
                "cache_working": cached_value == test_value,
                "cache_backend": str(type(cache))
            }
        except Exception as e:
            results["cache_test"] = {
                "status": "error",
                "error": str(e)
            }
        
        # Overall status
        all_tests_passed = all(
            test.get("status") == "success" 
            for test in [results["database_info"], results["connection_test"], 
                        results["query_test"], results["cache_test"]]
        )
        
        results["status"] = "healthy" if all_tests_passed else "unhealthy"
        
        return Response(results, status=status.HTTP_200_OK)


def database_test_html(request):
    """HTML version of database test for browser viewing"""
    try:
        # Test database connection
        start_time = time.time()
        with connection.cursor() as cursor:
            cursor.execute("SELECT version()")
            db_version = cursor.fetchone()[0] if cursor.rowcount > 0 else "Unknown"
            
            cursor.execute("SELECT current_database()")
            db_name = cursor.fetchone()[0] if cursor.rowcount > 0 else "Unknown"
            
            cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'")
            table_count = cursor.fetchone()[0] if cursor.rowcount > 0 else 0
        
        connection_time = (time.time() - start_time) * 1000
        
        context = {
            'status': 'SUCCESS',
            'db_version': db_version,
            'db_name': db_name,
            'table_count': table_count,
            'connection_time': round(connection_time, 2),
            'host': settings.DATABASES['default'].get('HOST', 'unknown'),
            'port': settings.DATABASES['default'].get('PORT', 'unknown'),
            'engine': settings.DATABASES['default'].get('ENGINE', 'unknown'),
        }
        
    except Exception as e:
        context = {
            'status': 'ERROR',
            'error': str(e),
            'error_type': type(e).__name__,
        }
    
    return render(request, 'database_test.html', context)
