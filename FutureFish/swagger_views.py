"""
Custom Swagger views for Future Fish Dashboard API documentation.
This module provides custom Swagger UI integration using the existing swagger.yaml file.
"""

import os
from django.conf import settings
from django.http import HttpResponse
from django.views.generic import TemplateView


class CustomSwaggerView(TemplateView):
    """
    Custom Swagger UI view that serves the Swagger UI interface.
    The YAML content is loaded directly by the JavaScript.
    """
    template_name = 'swagger.html'


class SwaggerYAMLView(TemplateView):
    """
    View to serve the raw swagger.yaml file.
    """
    def get(self, request, *args, **kwargs):
        swagger_file_path = os.path.join(settings.BASE_DIR.parent, 'swagger.yaml')
        
        try:
            with open(swagger_file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            response = HttpResponse(content, content_type='text/yaml')
            response['Content-Disposition'] = 'inline; filename="swagger.yaml"'
            return response
        except FileNotFoundError:
            return HttpResponse('Swagger file not found', status=404)
        except Exception as e:
            return HttpResponse(f'Error reading swagger file: {str(e)}', status=500)


class SwaggerJSONView(TemplateView):
    """
    View to serve the swagger.yaml file as JSON (converted by Swagger UI).
    """
    def get(self, request, *args, **kwargs):
        swagger_file_path = os.path.join(settings.BASE_DIR.parent, 'swagger.yaml')
        
        try:
            import yaml
            import json
            
            with open(swagger_file_path, 'r', encoding='utf-8') as file:
                yaml_content = yaml.safe_load(file)
            
            json_content = json.dumps(yaml_content, indent=2)
            
            response = HttpResponse(json_content, content_type='application/json')
            response['Content-Disposition'] = 'inline; filename="swagger.json"'
            return response
        except ImportError:
            return HttpResponse('PyYAML not installed', status=500)
        except FileNotFoundError:
            return HttpResponse('Swagger file not found', status=404)
        except Exception as e:
            return HttpResponse(f'Error converting swagger file: {str(e)}', status=500)
