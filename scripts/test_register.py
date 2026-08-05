import os, django, json
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'worktrack.settings')
django.setup()
from django.test import Client

c = Client()

payload = json.dumps({
    'email': 'admin_test@example.com',
    'password': 'TestPass123!',
    'full_name': 'Admin Test',
    'is_admin': True
})

resp = c.post('/api/register/', data=payload, content_type='application/json')
print('STATUS', resp.status_code)
print(resp.content.decode())
