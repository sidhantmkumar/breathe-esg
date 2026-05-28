from django.contrib import admin
from .models import Client, DataIngestion, EmissionRecord, ReviewStatus, AuditLog

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'timezone', 'created_at']
    search_fields = ['name', 'slug']

@admin.register(DataIngestion)
class DataIngestionAdmin(admin.ModelAdmin):
    list_display = ['file_name', 'source_type', 'status', 'ingested_by', 'ingested_at']
    list_filter = ['source_type', 'status']
    search_fields = ['file_name']

@admin.register(EmissionRecord)
class EmissionRecordAdmin(admin.ModelAdmin):
    list_display = ['source_type', 'category', 'scope', 'raw_value', 'raw_unit', 'normalized_co2e', 'status', 'is_suspicious', 'is_locked']
    list_filter = ['source_type', 'status', 'scope', 'is_suspicious', 'is_locked']
    search_fields = ['category']

@admin.register(ReviewStatus)
class ReviewStatusAdmin(admin.ModelAdmin):
    list_display = ['record', 'status', 'reviewed_by', 'reviewed_at']
    list_filter = ['status']

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['action', 'performed_by', 'performed_at']
    list_filter = ['action']
    readonly_fields = ['id', 'record', 'ingestion', 'action', 'performed_by', 'before_state', 'after_state', 'performed_at']