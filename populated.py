import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'worktrack.settings')
import django

django.setup()

from django.contrib.auth.models import User
from reports.models import (
    Company,
    EmployeeProfile,
    DailyReport,
    WorkEntry,
    AssignedTask,
    ReassignmentLog,
    ChatRoom,
    ChatMessage,
    ChatReadStatus,
    PushSubscription,
)


def populate_database():
    company, created_company = Company.objects.get_or_create(
        name='Default Company',
        defaults={'is_active': True},
    )

    user, created_user = User.objects.get_or_create(
        username='seed-user@example.com',
        defaults={
            'first_name': 'Seed',
            'last_name': 'User',
            'email': 'seed-user@example.com',
            'is_active': True,
        },
    )

    if created_user:
        user.set_password('seed1234')
        user.save()

    employee_profile, created_profile = EmployeeProfile.objects.get_or_create(
        user=user,
        defaults={
            'company': company,
            'employee_id': 'EMP-001',
            'department': 'Operations',
            'designation': 'Seed User',
            'is_owner': False,
            'is_admin': False,
        },
    )

    return {
        'company': company.name,
        'company_created': created_company,
        'user_created': created_user,
        'profile_created': created_profile,
        'counts': {
            'users': User.objects.count(),
            'companies': Company.objects.count(),
            'employee_profiles': EmployeeProfile.objects.count(),
            'daily_reports': DailyReport.objects.count(),
            'work_entries': WorkEntry.objects.count(),
            'assigned_tasks': AssignedTask.objects.count(),
            'reassignment_logs': ReassignmentLog.objects.count(),
            'chat_rooms': ChatRoom.objects.count(),
            'chat_messages': ChatMessage.objects.count(),
            'chat_read_statuses': ChatReadStatus.objects.count(),
            'push_subscriptions': PushSubscription.objects.count(),
        },
    }


if __name__ == '__main__':
    print(populate_database())
