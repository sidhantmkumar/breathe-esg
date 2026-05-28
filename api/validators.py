from decimal import Decimal
from .models import EmissionRecord, AuditLog


def run_validation(records, ingestion):
    if not records:
        return

    co2e_values = [
        r.normalized_co2e for r in records
        if r.normalized_co2e is not None and r.normalized_co2e > 0
    ]
    avg_co2e = sum(co2e_values) / len(co2e_values) if co2e_values else Decimal('0')

    for record in records:
        reasons = []

        # Rule 1 - Negative values
        if record.raw_value < 0:
            reasons.append(
                f"Negative value detected: {record.raw_value} {record.raw_unit}."
            )

        # Rule 2 - Missing normalized value
        if record.normalized_co2e is None:
            reasons.append("Could not compute normalized CO2e value.")

        # Rule 3 - Suspicious spike 3x average
        if (
            record.normalized_co2e is not None
            and avg_co2e > 0
            and record.normalized_co2e > avg_co2e * 3
        ):
            reasons.append(
                f"Suspicious spike: {record.normalized_co2e:.2f} kg CO2e is "
                f"{(record.normalized_co2e / avg_co2e):.1f}x the batch average "
                f"of {avg_co2e:.2f} kg CO2e."
            )

        if reasons:
            # Flagged rows go to Needs Review queue
            record.is_suspicious = True
            record.status = EmissionRecord.Status.FLAGGED
            record.flag_reason = ' | '.join(reasons)
        else:
            # Clean rows auto-approve and lock
            record.status = EmissionRecord.Status.APPROVED
            record.is_locked = True
            record.flag_reason = None

        record.save()

        # Create audit log for auto-approved rows
        if not record.is_suspicious:
            AuditLog.objects.create(
                record=record,
                action=AuditLog.Action.APPROVED,
                performed_by='system',
                before_state={'status': 'uploaded'},
                after_state={'status': 'approved', 'is_locked': True}
            )