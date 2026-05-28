import csv
import io
from datetime import datetime
from decimal import Decimal

UNIT_TO_LITRES = {
    'L': Decimal('1'),
    'l': Decimal('1'),
    'KL': Decimal('1000'),
    'kl': Decimal('1000'),
    'GAL': Decimal('3.785'),
    'gal': Decimal('3.785'),
    'IGAL': Decimal('4.546'),
}

DIESEL_CO2E_PER_LITRE = Decimal('2.68')

def parse_sap(file_content):
    reader = csv.DictReader(io.StringIO(file_content), delimiter=';')
    rows = []
    for raw_row in reader:
        row = {k.strip(): v.strip() for k, v in raw_row.items() if k}
        menge = row.get('Menge', row.get('menge', ''))
        einheit = row.get('Einheit', row.get('einheit', 'L'))
        datum = row.get('Buchungsdatum', row.get('buchungsdatum', ''))

        if not menge:
            continue

        menge_clean = menge.replace('.', '').replace(',', '.')
        try:
            raw_val = Decimal(menge_clean)
        except Exception:
            continue

        unit = einheit.strip().upper() if einheit else 'L'
        multiplier = UNIT_TO_LITRES.get(unit, Decimal('1'))
        litres = raw_val * multiplier
        co2e = litres * DIESEL_CO2E_PER_LITRE

        period_start = None
        period_end = None
        if datum:
            for fmt in ('%d.%m.%Y', '%Y-%m-%d', '%m/%d/%Y'):
                try:
                    period_start = datetime.strptime(datum, fmt).date()
                    period_end = period_start
                    break
                except ValueError:
                    continue

        rows.append({
            'scope': 1,
            'category': 'stationary_combustion',
            'raw_value': raw_val,
            'raw_unit': einheit or 'L',
            'normalized_co2e': co2e,
            'period_start': period_start,
            'period_end': period_end,
            'raw_payload': row,
        })
    return rows