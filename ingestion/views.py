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
import socket
import requests

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
        description="Tests database connectivity, query performance, displays connection info, and checks IP whitelist status",
        responses={
            200: {
                "type": "object",
                "properties": {
                    "status": {"type": "string"},
                    "database_info": {"type": "object"},
                    "connection_test": {"type": "object"},
                    "query_test": {"type": "object"},
                    "cache_test": {"type": "object"},
                    "network_test": {"type": "object"}
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
            "cache_test": {},
            "network_test": {}
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

        # Test 2: Network Connectivity and IP Check
        try:
            db_host = settings.DATABASES['default'].get('HOST', '')
            db_port = int(settings.DATABASES['default'].get('PORT', 5432))
            
            # Get our outbound IP address
            try:
                # Try multiple services to get our IP
                ip_services = [
                    'https://api.ipify.org',
                    'https://httpbin.org/ip',
                    'https://icanhazip.com'
                ]
                our_ip = None
                for service in ip_services:
                    try:
                        response = requests.get(service, timeout=5)
                        if service == 'https://httpbin.org/ip':
                            our_ip = response.json().get('origin', '').split(',')[0].strip()
                        else:
                            our_ip = response.text.strip()
                        if our_ip:
                            break
                    except:
                        continue
            except Exception as ip_error:
                our_ip = f"Could not determine: {str(ip_error)}"
            
            # Test DNS resolution
            try:
                resolved_ip = socket.gethostbyname(db_host)
                dns_status = "success"
                dns_error = None
            except Exception as dns_e:
                resolved_ip = "failed"
                dns_status = "error"
                dns_error = str(dns_e)
            
            # Test TCP connectivity to database port
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(10)
                tcp_start = time.time()
                result = sock.connect_ex((db_host, db_port))
                tcp_time = (time.time() - tcp_start) * 1000
                sock.close()
                
                tcp_status = "success" if result == 0 else "failed"
                tcp_error = None if result == 0 else f"Connection refused (code: {result})"
            except Exception as tcp_e:
                tcp_status = "error"
                tcp_error = str(tcp_e)
                tcp_time = 0
            
            results["network_test"] = {
                "status": "success" if dns_status == "success" and tcp_status == "success" else "error",
                "our_outbound_ip": our_ip,
                "database_host": db_host,
                "database_port": db_port,
                "dns_resolution": {
                    "status": dns_status,
                    "resolved_ip": resolved_ip,
                    "error": dns_error
                },
                "tcp_connectivity": {
                    "status": tcp_status,
                    "connection_time_ms": round(tcp_time, 2) if tcp_status != "error" else 0,
                    "error": tcp_error
                },
                "whitelist_check": {
                    "message": "If TCP connection fails, check if this IP is whitelisted in your database",
                    "recommended_action": f"Add {our_ip} to your database whitelist" if our_ip and not our_ip.startswith("Could not") else "Check your database whitelist settings",
                    "render_static_ips": [
                        "3.95.140.172/30",
                        "3.95.140.176/30", 
                        "44.194.54.40/30",
                        "44.194.54.44/30"
                    ]
                }
            }
        except Exception as e:
            results["network_test"] = {
                "status": "error",
                "error": str(e),
                "error_type": type(e).__name__
            }
        
        # Test 3: Basic Connection Test
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
                "error_type": type(e).__name__,
                "possible_causes": [
                    "Database server is down",
                    "Incorrect database credentials",
                    "IP address not whitelisted in database",
                    "Network connectivity issues",
                    "Database connection limit reached"
                ]
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
            for test in [results["database_info"], results["network_test"], 
                        results["connection_test"], results["query_test"], results["cache_test"]]
        )
        
        results["status"] = "healthy" if all_tests_passed else "unhealthy"
        
        return Response(results, status=status.HTTP_200_OK)


def database_test_html(request):
    """HTML version of database test for browser viewing - always renders"""
    context = {
        'status': 'TESTING',
        'timestamp': time.strftime("%Y-%m-%d %H:%M:%S UTC"),
        'our_ip': 'Checking...',
        'host': 'Unknown',
        'port': 'Unknown',
        'engine': 'Unknown',
        'error': None,
        'error_type': None,
        'db_version': None,
        'db_name': None,
        'table_count': None,
        'connection_time': None,
    }
    
    # Step 1: Get basic database config (this should always work)
    try:
        db_settings = settings.DATABASES.get('default', {})
        context.update({
            'host': db_settings.get('HOST', 'Not configured'),
            'port': db_settings.get('PORT', 'Not configured'),
            'engine': db_settings.get('ENGINE', 'Not configured'),
        })
    except Exception as e:
        context['error'] = f"Settings error: {str(e)}"
    
    # Step 2: Get our outbound IP (independent of database)
    try:
        ip_response = requests.get('https://api.ipify.org', timeout=10)
        context['our_ip'] = ip_response.text.strip()
    except Exception as e:
        context['our_ip'] = f"Could not determine: {str(e)}"
    
    # Step 3: Test database connection with simple approach
    try:
        start_time = time.time()
        
        with connection.cursor() as cursor:
            cursor.execute("SELECT version()")
            db_version = cursor.fetchone()
            context['db_version'] = db_version[0] if db_version else "Unknown"
            
            cursor.execute("SELECT current_database()")
            db_name = cursor.fetchone()
            context['db_name'] = db_name[0] if db_name else "Unknown"
            
            cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'")
            table_count = cursor.fetchone()
            context['table_count'] = table_count[0] if table_count else 0
        
        connection_time = (time.time() - start_time) * 1000
        context.update({
            'status': 'SUCCESS',
            'connection_time': round(connection_time, 2),
        })
            
    except Exception as e:
        context.update({
            'status': 'ERROR',
            'error': str(e),
            'error_type': type(e).__name__
        })
    finally:
        # Always close the connection to prevent hanging
        try:
            connection.close()
        except:
            pass
    
    # Always render the template, regardless of database status
    return render(request, 'database_test.html', context)
