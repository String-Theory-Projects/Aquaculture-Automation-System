"""
Swagger/OpenAPI Configuration for Future Fish Dashboard

This module contains all the configuration settings for drf-spectacular
to generate comprehensive API documentation.
"""

SPECTACULAR_SETTINGS = {
    'TITLE': 'Future Fish Dashboard API',
    'DESCRIPTION': '''
Comprehensive API documentation for the Future Fish Dashboard project.

This API provides endpoints for:
- Automation management (thresholds, schedules, execution)
- Pond management and monitoring
- User authentication and profiles
- Analytics and data visualization
- Device control and monitoring

## Project Phases
- **Phase 1**: Core infrastructure and basic pond management
- **Phase 2**: User authentication and basic automation
- **Phase 3**: Advanced automation and scheduling
- **Phase 4**: Analytics and reporting
- **Phase 5**: Device control and real-time monitoring

## 🔐 Authentication Setup

### Step 1: Get Your JWT Token
1. Use the authentication endpoints to login/register
2. Copy the JWT token from the response

### Step 2: Configure Authorization
1. Click the **"Authorize"** button at the top of this page
2. Enter your token in the format: `Bearer <your_jwt_token>`
3. Click **"Authorize"** to save

### Step 3: Test Endpoints
- All authenticated endpoints will now automatically include your token
- You can also manually add the header: `Authorization: Bearer <your_jwt_token>`

## 📍 Base URLs
- **Development**: `http://localhost:8000`
- **Production**: `https://app.futurefishagro.com`

## ⚡ Rate Limiting
API requests are limited to 100 requests per hour per user.

## 📚 Documentation Updates
This documentation is updated with each project phase completion to reflect new endpoints and features.

## 🚀 Quick Start
1. **Authorize** using the button above
2. **Select a server** from the dropdown
3. **Browse endpoints** by category
4. **Test endpoints** with the "Try it out" button
    ''',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'SERVE_PUBLIC': True,
    'COMPONENT_SPLIT_REQUEST': True,
    'SORT_OPERATIONS': True,
    'SORT_OPERATION_PARAMETERS': True,
    'CAMELIZE_NAMES': False,
    'POSTPROCESSING_HOOKS': [],
    'PREPROCESSING_HOOKS': [],
    
    # Contact and License Information
    'CONTACT': {
        'name': 'Future Fish Engineering Team',
        'email': 'engineering@futurefishagro.com',
        'url': 'https://futurefishagro.com',
    },
    'LICENSE': {
        'name': 'Proprietary',
        'url': 'https://futurefishagro.com/license',
    },
    
    # API Tags for Organization
    'TAGS': [
        {
            'name': 'Authentication',
            'description': 'User authentication, registration, and JWT token management'
        },
        {
            'name': 'Users',
            'description': 'User profile management and account operations'
        },
        {
            'name': 'Automation - Thresholds',
            'description': 'Sensor threshold management and automation triggers'
        },
        {
            'name': 'Automation - Schedules',
            'description': 'Automation schedule management and configuration'
        },
        {
            'name': 'Automation - Execution',
            'description': 'Manual automation execution and control'
        },
        {
            'name': 'Automation - Device Control',
            'description': 'Direct device command execution and control'
        },
        {
            'name': 'Automation - Monitoring',
            'description': 'System monitoring and status information'
        },
        {
            'name': 'Automation - History',
            'description': 'Automation execution history and analytics'
        },
        {
            'name': 'Ponds',
            'description': 'Pond management and monitoring endpoints'
        },
        {
            'name': 'Analytics',
            'description': 'Data analytics and visualization endpoints'
        },
        {
            'name': 'Dashboard',
            'description': 'Main dashboard functionality and controls'
        }
    ],
    
    # Server Configuration
    'SERVERS': [
        {
            'url': 'http://localhost:8000',
            'description': 'Development server',
            'variables': {
                'baseUrl': {
                    'default': 'http://localhost:8000',
                    'description': 'Base URL for the API'
                }
            }
        }
    ],
    
    # Security Configuration
    'SECURITY': [
        {
            'BearerAuth': []
        }
    ],
    
    # Swagger UI Settings
    'SWAGGER_UI_SETTINGS': {
        'deepLinking': True,
        'persistAuthorization': True,
        'displayOperationId': True,
        'filter': True,
        'tryItOutEnabled': True,
        'requestInterceptor': 'function(request) { console.log("Request:", request); return request; }',
        'responseInterceptor': 'function(response) { console.log("Response:", response); return response; }',
        'docExpansion': 'list',  # Can be 'list', 'full', 'none'
        'defaultModelsExpandDepth': 2,
        'defaultModelExpandDepth': 2,
        'displayRequestDuration': True,
        'showExtensions': True,
        'showCommonExtensions': True,
        'supportedSubmitMethods': ['get', 'post', 'put', 'delete', 'patch'],
        'oauth2RedirectUrl': '/swagger/oauth2-redirect.html',
    },
    
    # Redoc UI Settings
    'REDOC_UI_SETTINGS': {
        'hideDownloadButton': False,
        'hideHostname': False,
        'hideLoading': False,
        'hideSingleRequestSampleTab': False,
        'jsonSampleExpandLevel': 2,
        'menuToggle': True,
        'nativeScrollbars': False,
        'noAutoAuth': False,
        'pathInMiddlePanel': False,
        'requiredPropsFirst': True,
        'scrollYOffset': 0,
        'showExtensions': True,
        'sortPropsAlphabetically': True,
        'suppressWarnings': False,
        'theme': {
            'colors': {
                'primary': {
                    'main': '#1976d2'
                }
            },
            'typography': {
                'fontSize': '14px',
                'lineHeight': '1.5em',
                'code': {
                    'fontSize': '13px',
                    'fontFamily': 'Monaco, Consolas, "Lucida Console", monospace'
                }
            },
            'sidebar': {
                'width': '260px'
            }
        }
    },
    
    # Schema Generation Settings
    'SCHEMA_PATH_PREFIX': '/api/v1/',
    'SCHEMA_PATH_PREFIX_TRIM': True,
    'SCHEMA_PATH_PREFIX_INSERT': '',
    'SCHEMA_COERCE_PATH_PK': True,
    'SCHEMA_COERCE_PATH_PK_SUFFIX': True,
    
    # Component Settings
    'COMPONENT_SPLIT_PATCH': True,
    'COMPONENT_NO_READ_ONLY_REQUIRED': False,
    
    # Authentication Whitelist
    'AUTHENTICATION_WHITELIST': [],
    
    # Custom Extensions
    'EXTENSIONS_INFO': {
        'x-logo': {
            'url': '/static/img/logo.png',
            'altText': 'Future Fish Dashboard'
        }
    },
    
    # API Versioning
    'OAS_VERSION': '3.0.3',
    'SCHEMA_GENERATOR': 'rest_framework.schemas.openapi.AutoSchema',
    
    # Enum Settings
    'ENUM_NAME_OVERRIDES': {},
    'ENUM_GENERATE_CHOICE_DESCRIPTION': True,
    
    # Error Handling
    'DISABLE_ERRORS_AND_WARNINGS': False,
    'ENABLE_DJANGO_DEPLOY_CHECK': True,
}

# Production-specific server configuration
PRODUCTION_SERVERS = [
    {
        'url': 'https://app.futurefishagro.com',
        'description': 'Production server',
        'variables': {
            'baseUrl': {
                'default': 'https://app.futurefishagro.com',
                'description': 'Base URL for the API'
            }
        }
    }
]

def get_spectacular_settings(environment='development'):
    """
    Get SPECTACULAR_SETTINGS configuration for the specified environment.
    
    Args:
        environment (str): Either 'development' or 'production'
        
    Returns:
        dict: Complete SPECTACULAR_SETTINGS configuration
    """
    settings = SPECTACULAR_SETTINGS.copy()
    
    if environment == 'production':
        # Add production server to the servers list
        settings['SERVERS'].extend(PRODUCTION_SERVERS)
        
        # Production-specific modifications
        settings['SWAGGER_UI_SETTINGS']['persistAuthorization'] = False
        settings['DISABLE_ERRORS_AND_WARNINGS'] = True
        
    return settings
