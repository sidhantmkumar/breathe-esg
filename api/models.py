import uuid
from django.db import models


class Client(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, max_length=100)
    timezone = models.CharField(max_length=64, default='UTC')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class DataIngestion(models.Model):

    class SourceType(models.TextChoices):
        SAP = 'sap', 'SAP Fuel/Procurement'
        UTILITY = 'utility', 'Utility Electricity'
        TRAVEL = 'travel', 'Corporate Travel'

    class Status(models.TextChoices):
        UPLOADED = 'uploaded', 'Uploaded'
        UNDER_REVIEW = 'under_review', 'Under Review'
        PARTIALLY_APPROVED = 'partially_approved', 'Partially Approved'
        FINALIZED = 'finalized', 'Finalized'
        REJECTED = 'rejected', 'Rejected'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name='ingestions')
    source_type = models.CharField(max_length=20, choices=SourceType.choices)
    file_name = models.CharField(max_length=255)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.UPLOADED)
    error_log = models.TextField(blank=True, null=True)
    ingested_at = models.DateTimeField(auto_now_add=True)
    ingested_by = models.CharField(max_length=150)

    class Meta:
        ordering = ['-ingested_at']

    def __str__(self):
        return f"{self.source_type} — {self.file_name} ({self.status})"


class EmissionRecord(models.Model):

    class SourceType(models.TextChoices):
        SAP = 'sap', 'SAP'
        UTILITY = 'utility', 'Utility'
        TRAVEL = 'travel', 'Travel'

    class Status(models.TextChoices):
        UPLOADED = 'uploaded', 'Uploaded'
        VALIDATED = 'validated', 'Validated'
        FLAGGED = 'flagged', 'Flagged'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'

    class Scope(models.IntegerChoices):
        SCOPE_1 = 1, 'Scope 1 — Direct Emissions'
        SCOPE_2 = 2, 'Scope 2 — Purchased Electricity'
        SCOPE_3 = 3, 'Scope 3 — Indirect Emissions'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name='records')
    ingestion = models.ForeignKey(DataIngestion, on_delete=models.PROTECT, related_name='records')

    scope = models.IntegerField(choices=Scope.choices)
    category = models.CharField(max_length=100)
    source_type = models.CharField(max_length=20, choices=SourceType.choices)

    raw_value = models.DecimalField(max_digits=20, decimal_places=6)
    raw_unit = models.CharField(max_length=50)
    normalized_co2e = models.DecimalField(max_digits=20, decimal_places=6, null=True, blank=True)
    normalized_unit = models.CharField(max_length=50, default='kg CO2e')

    raw_payload = models.JSONField(default=dict)

    is_edited = models.BooleanField(default=False)
    is_suspicious = models.BooleanField(default=False)
    is_locked = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.UPLOADED)
    flag_reason = models.TextField(blank=True, null=True)

    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['client', 'status']),
            models.Index(fields=['client', 'is_suspicious']),
            models.Index(fields=['ingestion', 'status']),
        ]

    def __str__(self):
        return f"{self.source_type} | {self.category} | {self.raw_value} {self.raw_unit} | {self.status}"


class ReviewStatus(models.Model):

    class Status(models.TextChoices):
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
        FLAGGED = 'flagged', 'Flagged'
        NEEDS_REVIEW = 'needs_review', 'Needs Review'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    record = models.ForeignKey(EmissionRecord, on_delete=models.PROTECT, related_name='reviews')
    status = models.CharField(max_length=20, choices=Status.choices)
    reviewed_by = models.CharField(max_length=150)
    notes = models.TextField(blank=True, null=True)
    override_reason = models.TextField(blank=True, null=True)
    reviewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-reviewed_at']

    def __str__(self):
        return f"{self.record_id} — {self.status} by {self.reviewed_by}"


class AuditLog(models.Model):

    class Action(models.TextChoices):
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
        EDITED = 'edited', 'Edited'
        FLAGGED = 'flagged', 'Flagged'
        UNLOCKED = 'unlocked', 'Unlocked'
        BATCH_REJECTED = 'batch_rejected', 'Batch Rejected'
        EXPORTED = 'exported', 'Exported'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    record = models.ForeignKey(
        EmissionRecord, on_delete=models.PROTECT,
        related_name='audit_logs', null=True, blank=True
    )
    ingestion = models.ForeignKey(
        DataIngestion, on_delete=models.PROTECT,
        related_name='audit_logs', null=True, blank=True
    )
    action = models.CharField(max_length=30, choices=Action.choices)
    performed_by = models.CharField(max_length=150)
    before_state = models.JSONField(default=dict)
    after_state = models.JSONField(default=dict)
    performed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-performed_at']

    def __str__(self):
        return f"{self.action} by {self.performed_by} at {self.performed_at}"
