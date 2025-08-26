"""
URL configuration for data_warehouse project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # SQL Explorer URLs
    path('', include('explorer.urls')),
    
    # SQL Explorer URLs
    path('explorer/', include('explorer.urls')),
    
    # Authentication URLs (if needed)
    path('accounts/', include('django.contrib.auth.urls')),
    
    # Dashboard redirect to explorer
    path('dashboard/', RedirectView.as_view(url='/explorer/', permanent=False), name='dashboard'),
    
    # Monitoring URLs (direct access)
    path('monitoring/', RedirectView.as_view(url='/ingestion/monitoring/', permanent=False), name='monitoring'),
    
    # Ingestion module URLs
    path('ingestion/', include('ingestion.urls')),

    # Reports module URLs
    path('reports/', include('reports.urls')),
    
    # CRM Test Dashboard URLs
    path('testing/', include('ingestion.tests.urls')),
]
