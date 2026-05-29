
import csv
import json
from django.http import HttpResponse
from django.contrib.auth import authenticate, login, logout
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.response import Response
from .models import Client, DataIngestion, EmissionRecord, ReviewStatus, AuditLog
from .serializers import (
    ClientSerializer, DataIngestionSerializer,
    EmissionRecordSerializer, EmissionRecordListSerializer,
    ReviewStatusSerializer, AuditLogSerializer
)
from .parsers.sap_parser import parse_sap
from .parsers.utility_parser import parse_utility
from .parsers.travel_parser import parse_travel
from .validators import run_validation


# ── Auth ──────────────────────────────────────────────────────────────────────
@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    username = request.data.get('username')
    password = request.data.get('password')
    user = authenticate(request, username=username, password=password)
    if user:
        login(request, user)
        return Response({'username': user.username})
    return Response({'error': 'Invalid credentials'}, status=400)


@api_view(['POST'])
def logout_view(request):
    logout(request)
    return Response({'message': 'Logged out'})


@api_view(['GET'])
@permission_classes([AllowAny])
def me_view(request):
    if request.user.is_authenticated:
        return Response({'username': request.user.username, 'authenticated': True})
    return Response({'authenticated': False})


# ── Clients ───────────────────────────────────────────────────────────────────

@api_view(['GET'])
def client_list(request):
    clients = Client.objects.all()
    return Response(ClientSerializer(clients, many=True).data)


# ── Upload ────────────────────────────────────────────────────────────────────

@api_view(['POST'])
def upload_file(request):
    client_id = request.data.get('client_id')
    source_type = request.data.get('source_type')
    file = request.FILES.get('file')

    if not all([client_id, source_type, file]):
        return Response({'error': 'client_id, source_type, and file are required'}, status=400)

    try:
        client = Client.objects.get(id=client_id)
    except Client.DoesNotExist:
        return Response({'error': 'Client not found'}, status=404)

    ingestion = DataIngestion.objects.create(
        client=client,
        source_type=source_type,
        file_name=file.name,
        status=DataIngestion.Status.UPLOADED,
        ingested_by=request.user.username
    )

    try:
        file_content = file.read().decode('utf-8', errors='replace')
        if source_type == 'sap':
            rows = parse_sap(file_content)
        elif source_type == 'utility':
            rows = parse_utility(file_content)
        elif source_type == 'travel':
            rows = parse_travel(file_content)
        else:
            return Response({'error': 'Invalid source_type'}, status=400)

        records = []
        for row in rows:
            record = EmissionRecord.objects.create(
                client=client,
                ingestion=ingestion,
                scope=row['scope'],
                category=row['category'],
                source_type=source_type,
                raw_value=row['raw_value'],
                raw_unit=row['raw_unit'],
                normalized_co2e=row.get('normalized_co2e'),
                raw_payload=row.get('raw_payload', {}),
                period_start=row.get('period_start'),
                period_end=row.get('period_end'),
                status=EmissionRecord.Status.UPLOADED,
            )
            records.append(record)

        run_validation(records, ingestion)
        ingestion.status = DataIngestion.Status.UNDER_REVIEW
        ingestion.save()

        return Response({
            'message': f'{len(records)} rows ingested successfully',
            'ingestion_id': str(ingestion.id),
            'rows': len(records)
        })

    except Exception as e:
        ingestion.status = DataIngestion.Status.REJECTED
        ingestion.error_log = str(e)
        ingestion.save()
        return Response({'error': str(e)}, status=500)


# ── Records ───────────────────────────────────────────────────────────────────

@api_view(['GET'])
def record_list(request):
    client_id = request.query_params.get('client_id')
    source_type = request.query_params.get('source_type')
    status_filter = request.query_params.get('status')
    suspicious = request.query_params.get('suspicious')
    ingestion_id = request.query_params.get('ingestion_id')

    records = EmissionRecord.objects.filter(is_deleted=False)

    if client_id:
        records = records.filter(client_id=client_id)
    if source_type:
        records = records.filter(source_type=source_type)
    if status_filter:
        records = records.filter(status=status_filter)
    if suspicious == 'true':
        records = records.filter(is_suspicious=True)
    if ingestion_id:
        records = records.filter(ingestion_id=ingestion_id)

    serializer = EmissionRecordListSerializer(records, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def record_detail(request, pk):
    try:
        record = EmissionRecord.objects.get(id=pk, is_deleted=False)
    except EmissionRecord.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)
    return Response(EmissionRecordSerializer(record).data)


# ── Row Actions ───────────────────────────────────────────────────────────────

@api_view(['POST'])
def approve_record(request, pk):
    try:
        record = EmissionRecord.objects.get(id=pk, is_deleted=False)
    except EmissionRecord.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)

    if record.is_locked:
        return Response({'error': 'Record is locked and cannot be modified'}, status=400)

    before = EmissionRecordSerializer(record).data

    record.status = EmissionRecord.Status.APPROVED
    record.is_locked = True
    record.save()

    ReviewStatus.objects.create(
        record=record,
        status=ReviewStatus.Status.APPROVED,
        reviewed_by=request.user.username,
        notes=request.data.get('notes', '')
    )

    AuditLog.objects.create(
        record=record,
        action=AuditLog.Action.APPROVED,
        performed_by=request.user.username,
        before_state=before,
        after_state=EmissionRecordSerializer(record).data
    )

    return Response({'message': 'Record approved and locked'})


@api_view(['POST'])
def reject_record(request, pk):
    try:
        record = EmissionRecord.objects.get(id=pk, is_deleted=False)
    except EmissionRecord.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)

    if record.is_locked:
        return Response({'error': 'Record is locked and cannot be modified'}, status=400)

    before = EmissionRecordSerializer(record).data

    record.status = EmissionRecord.Status.REJECTED
    record.save()

    ReviewStatus.objects.create(
        record=record,
        status=ReviewStatus.Status.REJECTED,
        reviewed_by=request.user.username,
        notes=request.data.get('notes', '')
    )

    AuditLog.objects.create(
        record=record,
        action=AuditLog.Action.REJECTED,
        performed_by=request.user.username,
        before_state=before,
        after_state=EmissionRecordSerializer(record).data
    )

    return Response({'message': 'Record rejected'})


@api_view(['POST'])
def edit_record(request, pk):
    try:
        record = EmissionRecord.objects.get(id=pk, is_deleted=False)
    except EmissionRecord.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)

    if record.is_locked:
        return Response({'error': 'Record is locked. Cannot edit approved records.'}, status=400)

    override_reason = request.data.get('override_reason')
    if not override_reason:
        return Response({'error': 'override_reason is required when editing a record'}, status=400)

    before = EmissionRecordSerializer(record).data

    if 'normalized_co2e' in request.data:
        record.normalized_co2e = request.data['normalized_co2e']
    if 'raw_value' in request.data:
        record.raw_value = request.data['raw_value']
    if 'category' in request.data:
        record.category = request.data['category']
    if 'scope' in request.data:
        record.scope = request.data['scope']
    if 'period_start' in request.data:
        record.period_start = request.data['period_start']
    if 'period_end' in request.data:
        record.period_end = request.data['period_end']

    record.is_edited = True
    record.save()

    ReviewStatus.objects.create(
        record=record,
        status=ReviewStatus.Status.NEEDS_REVIEW,
        reviewed_by=request.user.username,
        notes=request.data.get('notes', ''),
        override_reason=override_reason
    )

    AuditLog.objects.create(
        record=record,
        action=AuditLog.Action.EDITED,
        performed_by=request.user.username,
        before_state=before,
        after_state=EmissionRecordSerializer(record).data
    )

    return Response({'message': 'Record edited successfully'})


# ── Batch Actions ─────────────────────────────────────────────────────────────

@api_view(['POST'])
def reject_batch(request, ingestion_id):
    try:
        ingestion = DataIngestion.objects.get(id=ingestion_id)
    except DataIngestion.DoesNotExist:
        return Response({'error': 'Batch not found'}, status=404)

    ingestion.status = DataIngestion.Status.REJECTED
    ingestion.save()

    EmissionRecord.objects.filter(
        ingestion=ingestion,
        status__in=['uploaded', 'validated', 'flagged']
    ).update(status=EmissionRecord.Status.REJECTED)

    AuditLog.objects.create(
        ingestion=ingestion,
        action=AuditLog.Action.BATCH_REJECTED,
        performed_by=request.user.username,
        before_state={'status': 'under_review'},
        after_state={'status': 'rejected'}
    )

    return Response({'message': 'Batch rejected'})


@api_view(['GET'])
def ingestion_list(request):
    client_id = request.query_params.get('client_id')
    ingestions = DataIngestion.objects.all()
    if client_id:
        ingestions = ingestions.filter(client_id=client_id)
    return Response(DataIngestionSerializer(ingestions, many=True).data)


# ── Export ────────────────────────────────────────────────────────────────────

@api_view(['GET'])
def export_approved(request, ingestion_id):
    try:
        ingestion = DataIngestion.objects.get(id=ingestion_id)
    except DataIngestion.DoesNotExist:
        return Response({'error': 'Batch not found'}, status=404)

    records = EmissionRecord.objects.filter(
        ingestion=ingestion,
        status=EmissionRecord.Status.APPROVED,
        is_deleted=False
    )

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="approved_{ingestion_id}.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'id', 'source_type', 'category', 'scope',
        'raw_value', 'raw_unit', 'normalized_co2e', 'normalized_unit',
        'period_start', 'period_end', 'is_edited', 'created_at'
    ])

    for r in records:
        writer.writerow([
            str(r.id), r.source_type, r.category, r.scope,
            r.raw_value, r.raw_unit, r.normalized_co2e, r.normalized_unit,
            r.period_start, r.period_end, r.is_edited, r.created_at
        ])

    ingestion.status = DataIngestion.Status.FINALIZED
    ingestion.save()

    EmissionRecord.objects.filter(ingestion=ingestion, status=EmissionRecord.Status.APPROVED).update(is_locked=True)

    AuditLog.objects.create(
        ingestion=ingestion,
        action=AuditLog.Action.EXPORTED,
        performed_by=request.user.username,
        before_state={'status': 'partially_approved'},
        after_state={'status': 'finalized'}
    )

    return response


# ── Dashboard Summary ─────────────────────────────────────────────────────────

@api_view(['GET'])
def dashboard_summary(request):
    client_id = request.query_params.get('client_id')
    records = EmissionRecord.objects.filter(is_deleted=False)
    if client_id:
        records = records.filter(client_id=client_id)

    return Response({
        'total': records.count(),
        'approved': records.filter(status='approved').count(),
        'rejected': records.filter(status='rejected').count(),
        'flagged': records.filter(status='flagged').count(),
        'needs_review': records.filter(is_suspicious=True).count(),
        'by_scope': {
            'scope_1': records.filter(scope=1).count(),
            'scope_2': records.filter(scope=2).count(),
            'scope_3': records.filter(scope=3).count(),
        },
        'by_source': {
            'sap': records.filter(source_type='sap').count(),
            'utility': records.filter(source_type='utility').count(),
            'travel': records.filter(source_type='travel').count(),
        }
    })


# ── Audit Log ─────────────────────────────────────────────────────────────────

@api_view(['GET'])
def audit_log_list(request):
    client_id = request.query_params.get('client_id')
    logs = AuditLog.objects.all()
    if client_id:
        logs = logs.filter(record__client_id=client_id)
    return Response(AuditLogSerializer(logs, many=True).data)