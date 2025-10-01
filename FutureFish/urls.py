"""
URL configuration for FutureFish project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from .swagger_views import CustomSwaggerView, SwaggerYAMLView, SwaggerJSONView

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Health check endpoint
    path('api/', include('core.urls')),
    
    # New modular app URLs
    path('api/v1/', include('api.urls')),
    path('ponds/', include('ponds.urls')),
    path('automation/', include('automation.urls')),
    path('analytics/', include('analytics.urls')),
    path('users/', include('users.urls')),
    
    # QR Generator
    path('qr-generator/', include('qr_generator.urls')),
    

    
    # API Documentation (Swagger)
    path('swagger/', CustomSwaggerView.as_view(), name='swagger-ui'),
    path('swagger.yaml', SwaggerYAMLView.as_view(), name='swagger-yaml'),
    path('swagger.json', SwaggerJSONView.as_view(), name='swagger-json'),
]

# Serve static files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    # In production, we still need to serve media files for QR codes
    # Railway will handle this through whitenoise or similar
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Admin site customization
admin.site.site_header = "Future Fish Dashboard Admin"
admin.site.site_title = "Future Fish Dashboard"
admin.site.index_title = "Welcome to Future Fish Dashboard Administration"
