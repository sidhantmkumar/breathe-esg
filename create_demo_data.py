import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'breathe_esg.settings')
django.setup()

from api.models import Client
from django.contrib.auth.models import User

if not Client.objects.filter(slug='acme-corp').exists():
    Client.objects.create(
        name='Acme Corp',
        slug='acme-corp',
        timezone='UTC'
    )
    print('Created Acme Corp client')
else:
    print('Acme Corp already exists')

if not User.objects.filter(username='analyst').exists():
    User.objects.create_superuser(
        username='analyst',
        email='analyst@acmecorp.com',
        password='analyst123'
    )
    print('Created analyst user')
else:
    print('analyst user already exists')

print('Demo data ready')