from rest_framework import serializers
from .models import Client, DataIngestion, EmissionRecord, ReviewStatus, AuditLog


class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = '__all__'


class DataIngestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataIngestion
        fields = '__all__'


class EmissionRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmissionRecord
        fields = '__all__'


class ReviewStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewStatus
        fields = '__all__'


class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = '__all__'


class EmissionRecordListSerializer(serializers.ModelSerializer):
    """Lighter serializer for dashboard list view"""
    class Meta:
        model = EmissionRecord
        fields = [
            'id', 'source_type', 'category', 'scope',
            'raw_value', 'raw_unit', 'normalized_co2e', 'normalized_unit',
            'status', 'is_suspicious', 'is_locked', 'is_edited', 'is_deleted',
            'flag_reason', 'period_start', 'period_end', 'created_at'
        ]