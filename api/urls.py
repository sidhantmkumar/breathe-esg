from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('auth/login/', views.login_view),
    path('auth/logout/', views.logout_view),
    path('auth/me/', views.me_view),

    # Clients
    path('clients/', views.client_list),

    # Upload
    path('upload/', views.upload_file),

    # Records
    path('records/', views.record_list),
    path('records/<uuid:pk>/', views.record_detail),
    path('records/<uuid:pk>/approve/', views.approve_record),
    path('records/<uuid:pk>/reject/', views.reject_record),
    path('records/<uuid:pk>/edit/', views.edit_record),

    # Batches
    path('ingestions/', views.ingestion_list),
    path('ingestions/<uuid:ingestion_id>/reject/', views.reject_batch),
    path('ingestions/<uuid:ingestion_id>/export/', views.export_approved),

    # Dashboard
    path('dashboard/summary/', views.dashboard_summary),

    # Audit
    path('audit/', views.audit_log_list),
]