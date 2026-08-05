import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'worktrack.settings')
import django
django.setup()
from django.contrib.auth.models import User
from reports.models import EmployeeProfile
from django.db import IntegrityError

email = 'a@company.com'
password = 'a1234'
# security_code = 'HAEGL2024'  # not enforced by backend

# remove existing user if any
existing = User.objects.filter(email=email)
if existing.exists():
    print('Existing user(s) found — deleting...')
    existing.delete()

# generate next employee id
maxn = 0
for eid in EmployeeProfile.objects.values_list('employee_id', flat=True):
    if not eid:
        continue
    try:
        num = int(eid.replace('EMP', ''))
        if num > maxn:
            maxn = num
    except Exception:
        continue
emp_id = f'EMP{maxn+1:03d}'

# create user
username = email
first_name = email.split('@')[0].capitalize()
user = User.objects.create_user(username=username, email=email, password=password, first_name=first_name)

# create profile
try:
    profile = EmployeeProfile.objects.create(user=user, employee_id=emp_id, department='Admin', designation='Admin', is_admin=True)
    print('Admin created:', user.email, '->', profile.employee_id)
except IntegrityError as e:
    print('Failed to create profile:', e)
    user.delete()
    raise

print('Done')
