from django.urls import path
from . import views

app_name = 'qr_generator'

urlpatterns = [
    path('', views.qr_generator_view, name='qr_generator'),
    path('result/<int:qr_id>/', views.qr_result_view, name='qr_result'),
    path('download/<int:qr_id>/', views.qr_download_view, name='qr_download'),
]
