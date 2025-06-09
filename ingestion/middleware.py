from django.http import HttpResponse
from django.utils.deprecation import MiddlewareMixin
import logging

logger = logging.getLogger(__name__)

class WordPressBlockerMiddleware(MiddlewareMixin):
    """Block WordPress-related requests that are causing 404s"""
    
    WORDPRESS_PATTERNS = [
        '/wp-content/',
        '/wp-admin/',
        '/wp-includes/',
        '/wp-json/',
        '/xmlrpc.php',
        '/wp-login.php',
        '/.well-known/',
        '/favicon.ico',
        '/robots.txt',
        '/sitemap.xml',
    ]
    
    def process_request(self, request):
        path = request.path_info.lower()
        
        # Block WordPress-related requests
        for pattern in self.WORDPRESS_PATTERNS:
            if pattern in path:
                logger.warning(f"Blocked WordPress request: {path}")
                return HttpResponse("Not Found", status=404)
        
        return None
