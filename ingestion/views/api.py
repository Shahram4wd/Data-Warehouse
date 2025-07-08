from django.shortcuts import render
from rest_framework import views, status
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from django.conf import settings

# Temporary stub to test URL resolver
class GeniusUserSyncView(views.APIView):
    def post(self, request, format=None):
        return Response({"message": "Stub implementation"})
