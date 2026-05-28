import csv
import io
from datetime import datetime
from decimal import Decimal

GRID_EMISSION_FACTOR = Decimal('0.233')

def parse_utility(file_content):
    reader = csv.DictReader(io.StringIO(file_content))
    rows = []
    for raw_row in reader:
        row = {k.strip(): v.strip() for k, v in raw_row.items() if k}
        value_str = row.get('consumption_value', '')
        unit = row.get('consumption_unit', 'kWh').strip()
        start_str = row.get('billing_period_start', '')
        end_str = row.get('billing_period_end', '')

        if not value_str:
            continue

        try:
            raw_val = Decimal(value_str)
        except Exception:
            continue

        if unit.lower() == 'mwh':
            kwh = raw_val * 1000
        else:
            kwh = raw_val

        co2e = kwh * GRID_EMISSION_FACTOR

        period_start = None
        period_end = None
        for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y'):
            try:
                if start_str:
                    period_start = datetime.strptime(start_str, fmt).date()
                if end_str:
                    period_end = datetime.strptime(end_str, fmt).date()
                break
            except ValueError:
                continue

        rows.append({
            'scope': 2,
            'category': 'purchased_electricity',
            'raw_value': raw_val,
            'raw_unit': unit,
            'normalized_co2e': co2e,
            'period_start': period_start,
            'period_end': period_end,
            'raw_payload': row,
        })
    return rows