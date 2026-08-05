from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from django.conf import settings
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db.models import Avg, Count
from django.db import transaction, IntegrityError
import re
from .models import EmployeeProfile, DailyReport, WorkEntry, AssignedTask, ReassignmentLog, ChatRoom, ChatMessage, ChatReadStatus, PushSubscription, Attendance
from .serializers import DailyReportSerializer, UserSerializer
from pywebpush import webpush, WebPushException

import json
import math
from django.core.mail import send_mail
from .models import Company, AdminInvite

from datetime import datetime, time as dt_time, timedelta, timezone as dt_timezone

# ── AUTO-STOP forgotten timers ──────────────────────────────────────
# If an employee forgets to click Stop, any entry still 'in_progress'
# past this hour (in this timezone) on its own date gets automatically
# marked completed the next time entries are listed — for the employee
# themselves, or for an admin viewing that employee's work log. There's
# no separate scheduled job: the check runs inline on every GET of
# entries, so a forgotten timer is closed out the next time either page
# is loaded, at the latest.
#
# NOTE: uses a fixed UTC+5:30 offset (India Standard Time) rather than
# zoneinfo.ZoneInfo('Asia/Kolkata') — zoneinfo needs the IANA tzdata
# database, which Windows Python does NOT ship by default (it requires
# installing the separate 'tzdata' pip package). Without it, every call
# raised ZoneInfoNotFoundError, which is why entries endpoints were
# returning 500s. A fixed offset needs no extra package and India
# doesn't observe daylight saving, so this is exact and dependency-free.
AUTO_STOP_HOUR = 19    # ← change this (0-23, 24-hour clock: 19 = 7 PM, 23 = 11 PM)
AUTO_STOP_MINUTE = 0   # ← and this (0-59)
AUTO_STOP_TIMEZONE = dt_timezone(timedelta(hours=5, minutes=30))


def _auto_stop_overdue_entries(entries_qs):
    """
    Finds every 'in_progress' entry in entries_qs whose own date has
    already passed AUTO_STOP_HOUR (7 PM) in AUTO_STOP_TIMEZONE, and
    closes it out exactly as if the employee had clicked Stop at 7 PM:
    adds the elapsed time (from start_time up to the 7 PM cutoff) to
    accumulated_minutes, sets actual_minutes/end_time/status, and
    appends a note to the remark so it's clear this wasn't a manual stop.
    """
    stale = entries_qs.filter(status='in_progress', start_time__isnull=False)
    for entry in stale:
        cutoff_local = datetime.combine(entry.date, dt_time(AUTO_STOP_HOUR, AUTO_STOP_MINUTE, 0), tzinfo=AUTO_STOP_TIMEZONE)
        now_local = timezone.now().astimezone(AUTO_STOP_TIMEZONE)
        if now_local < cutoff_local:
            continue  # this entry isn't overdue yet

        start_local = entry.start_time.astimezone(AUTO_STOP_TIMEZONE)
        elapsed_minutes = max(0, round((cutoff_local - start_local).total_seconds() / 60))

        entry.accumulated_minutes = (entry.accumulated_minutes or 0) + elapsed_minutes
        entry.actual_minutes = entry.accumulated_minutes
        entry.end_time = cutoff_local.astimezone(dt_timezone.utc)
        entry.status = 'completed'
        cutoff_label = cutoff_local.strftime('%I:%M %p').lstrip('0')
        note = f'[Auto-stopped at {cutoff_label} — timer was not stopped manually]'
        entry.remark = f'{entry.remark} {note}'.strip() if entry.remark else note
        entry.save()


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_admin_code_view(request):
    code = request.data.get('admin_code', '')
    is_valid = code == settings.ADMIN_SECURITY_CODE
    return Response({'valid': is_valid})


def generate_employee_id(company):
    maxn = 0
    qs = EmployeeProfile.objects.filter(company=company).values_list('employee_id', flat=True)
    for eid in qs:
        if not eid:
            continue
        try:
            num = int(eid.replace('EMP', ''))
            if num > maxn:
                maxn = num
        except Exception:
            continue
    return f'EMP{maxn+1:03d}'


def get_admin_profile_or_403(request):
    """
    Shared helper: returns (profile, None) if request.user is a valid admin,
    otherwise returns (None, error_response). Use like:
        profile, err = get_admin_profile_or_403(request)
        if err: return err
    """
    try:
        profile = request.user.employeeprofile
        if not profile.is_admin:
            return None, Response({'error': 'Forbidden'}, status=403)
        return profile, None
    except EmployeeProfile.DoesNotExist:
        return None, Response({'error': 'Forbidden'}, status=403)


def validate_password_strength(password):
    """
    Returns None if valid, or an error message string if invalid.
    Requires: min 8 chars, 1 uppercase, 1 lowercase, 1 number, 1 special character.
    """
    if not password or len(password) < 8:
        return 'Password must be at least 8 characters long.'
    if not re.search(r'[A-Z]', password):
        return 'Password must contain at least one uppercase letter.'
    if not re.search(r'[a-z]', password):
        return 'Password must contain at least one lowercase letter.'
    if not re.search(r'[0-9]', password):
        return 'Password must contain at least one number.'
    if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]~`]', password):
        return 'Password must contain at least one special character.'
    return None


@api_view(['POST'])
@permission_classes([AllowAny])
def google_admin_login_view(request):
    token = request.data.get('credential')
    company_name = request.data.get('company_name', '').strip()

    if not token:
        return Response({'error': 'Missing Google credential.'}, status=400)

    try:
        idinfo = id_token.verify_oauth2_token(
            token, google_requests.Request(), settings.GOOGLE_CLIENT_ID,
            clock_skew_in_seconds=10
        )
    except ValueError:
        return Response({'error': 'Invalid Google credential.'}, status=400)

    email = idinfo.get('email')
    email_verified = idinfo.get('email_verified', False)
    full_name = idinfo.get('name', '')

    if not email or not email_verified:
        return Response({'error': 'Google account email is not verified.'}, status=400)

    user_exists = User.objects.filter(email=email).exists()

    if not user_exists and not company_name:
        return Response({'error': 'Company name is required for new admin signup.'}, status=400)

    names = full_name.split(' ', 1)
    first_name = names[0] if names else ''
    last_name = names[1] if len(names) > 1 else ''

    user, created = User.objects.get_or_create(
        email=email,
        defaults={'username': email, 'first_name': first_name, 'last_name': last_name}
    )

    if created:
        user.set_unusable_password()
        user.save()
        company = Company.objects.create(name=company_name)
        emp_id = generate_employee_id(company)
        EmployeeProfile.objects.create(
            user=user, company=company, employee_id=emp_id,
            department='Admin', designation='Owner', is_admin=True, is_owner=True,
        )
    else:
        try:
            profile = user.employeeprofile
            if not profile.is_admin:
                return Response({'error': 'This email is already registered as an employee, not an admin.'}, status=403)
        except EmployeeProfile.DoesNotExist:
            return Response({'error': 'Account setup incomplete. Contact support.'}, status=403)

    token_obj, _ = Token.objects.get_or_create(user=user)
    serializer = UserSerializer(user, context={'request': request})
    return Response({
        'token': token_obj.key,
        'user': serializer.data,
        'is_admin': True,
        'company_name': user.employeeprofile.company.name,
    })


# LOGIN
# LOGIN
@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    email = request.data.get('email')
    password = request.data.get('password')

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return Response({'error': 'Invalid credentials'}, status=400)

    user = authenticate(username=user.username, password=password)
    if not user:
        return Response({'error': 'Invalid credentials'}, status=400)

    token, _ = Token.objects.get_or_create(user=user)

    try:
        profile = user.employeeprofile
        is_admin = profile.is_admin
        company_name = profile.company.name if profile.company else ''
    except EmployeeProfile.DoesNotExist:
        profile = None
        is_admin = False
        company_name = ''

    serializer = UserSerializer(user, context={'request': request})
    return Response({
        'token': token.key,
        'user': serializer.data,
        'is_admin': is_admin,
        'is_superuser': user.is_superuser,
        'company_name': company_name,
    })


# ── ADD EMPLOYEE (admin-only, company-scoped) ─────────────────────────
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def register_view(request):
    """
    Employees can NEVER self-signup. This endpoint only works when called
    by an authenticated admin, and the new employee is automatically
    placed into that admin's company.
    """
    try:
        requester_profile = request.user.employeeprofile
        if not requester_profile.is_admin:
            return Response({'error': 'Only admins can add employees.'}, status=403)
    except EmployeeProfile.DoesNotExist:
        return Response({'error': 'Only admins can add employees.'}, status=403)

    company = requester_profile.company
    email = request.data.get('email')
    password = request.data.get('password')
    full_name = request.data.get('full_name', '')
    department = request.data.get('department', 'General')
    designation = request.data.get('designation', 'Employee')

    if User.objects.filter(email=email).exists():
        return Response({'error': 'Email already exists'}, status=400)

    password_error = validate_password_strength(password)
    if password_error:
        return Response({'error': password_error}, status=400)

    names = full_name.split(' ', 1)
    first_name = names[0]
    last_name = names[1] if len(names) > 1 else ''

    try:
        with transaction.atomic():
            user = User.objects.create_user(
                username=email, email=email, password=password,
                first_name=first_name, last_name=last_name
            )
            emp_id = generate_employee_id(company)
            EmployeeProfile.objects.create(
                user=user, company=company, employee_id=emp_id,
                department=department, designation=designation, is_admin=False,
            )
    except Exception as e:
        print(f'Register error: {e}')
        return Response({'error': 'Registration failed'}, status=500)

    try:
        send_mail(
            subject='Welcome to WorkTrack — Your Login Credentials',
            message=f'''Hello {full_name},

Your WorkTrack account has been created by your admin.

Here are your login credentials:

Email: {email}
Password: {password}

Login here: {settings.FRONTEND_URL}

Please change your password after first login.

Regards,
WorkTrack Team''',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
        print(f'[OK] Email sent to {email}')
    except Exception as e:
        print(f'[ERROR] Email error: {e}')
        # Optionally notify user if email fails but don't fail the registration
        import logging
        logging.warning(f'Failed to send welcome email to {email}: {e}')

    token, _ = Token.objects.get_or_create(user=user)
    serializer = UserSerializer(user, context={'request': request})
    return Response({
        'token': token.key,
        'user': serializer.data,
        'is_admin': False
    })


# LOGOUT
@api_view(['POST'])
def logout_view(request):
    try:
        request.user.auth_token.delete()
    except:
        pass
    return Response({'message': 'Logged out'})


# GET CURRENT USER
@api_view(['GET'])
def me_view(request):
    user = request.user
    try:
        profile = user.employeeprofile
    except EmployeeProfile.DoesNotExist:
        profile = None

    photo_url = None
    if profile and getattr(profile, 'photo', None):
        try:
            photo_url = request.build_absolute_uri(profile.photo.url)
        except Exception:
            photo_url = None

    return Response({
        'id': user.id,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'full_name': user.get_full_name(),
        'profile': {
            'employee_id': profile.employee_id if profile else '',
            'department': profile.department if profile else '',
            'designation': profile.designation if profile else '',
            'phone': profile.phone if profile else '',
            'is_admin': profile.is_admin if profile else False,
            'is_owner': profile.is_owner if profile else False,
            'photo': photo_url,
        },
        'company_name': profile.company.name if profile and profile.company else '',
    })


# EMPLOYEE REPORTS
@api_view(['GET', 'POST'])
def reports_view(request):
    if request.method == 'GET':
        reports = DailyReport.objects.filter(employee=request.user)
        serializer = DailyReportSerializer(reports, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        serializer = DailyReportSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(employee=request.user)
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)


# SINGLE REPORT
@api_view(['GET', 'PUT', 'DELETE'])
def report_detail_view(request, pk):
    try:
        report = DailyReport.objects.get(pk=pk, employee=request.user)
    except DailyReport.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)

    if request.method == 'GET':
        return Response(DailyReportSerializer(report).data)
    elif request.method == 'PUT':
        serializer = DailyReportSerializer(report, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)
    elif request.method == 'DELETE':
        report.delete()
        return Response({'message': 'Deleted'})


# EMPLOYEE DASHBOARD STATS
@api_view(['GET'])
def employee_stats_view(request):
    reports = DailyReport.objects.filter(employee=request.user)
    return Response({
        'total_reports': reports.count(),
        'approved': reports.filter(status='approved').count(),
        'pending': reports.filter(status='pending').count(),
        'avg_hours': reports.aggregate(avg=Avg('hours_worked'))['avg'] or 0,
        'recent_reports': DailyReportSerializer(reports[:5], many=True).data
    })


@api_view(['GET'])
def employee_analytics_view(request):
    """Get comprehensive analytics data for employee dashboard"""
    from django.db.models import Sum, Q, F, Case, When
    from django.utils import timezone
    from datetime import timedelta, datetime
    from collections import defaultdict

    # Get the period filter (default to this month)
    period = request.query_params.get('period', 'month')
    today = timezone.now().date()

    if period == 'week':
        start_date = today - timedelta(days=today.weekday())
    elif period == 'quarter':
        start_date = today.replace(month=(today.month - 3) % 12 + 1, day=1)
    elif period == 'year':
        start_date = today.replace(month=1, day=1)
    else:  # month
        start_date = today.replace(day=1)

    # Get work entries for the period
    work_entries = WorkEntry.objects.filter(
        employee=request.user,
        date__gte=start_date,
        date__lte=today
    )

    # Calculate total hours
    total_minutes = work_entries.aggregate(
        total=Sum('actual_minutes')
    )['total'] or 0
    total_hours = total_minutes / 60

    # Calculate tasks
    total_entries = work_entries.count()
    completed_entries = work_entries.filter(status='completed').count()
    in_progress_entries = work_entries.filter(status='in_progress').count()
    not_started_entries = work_entries.filter(status='not_started').count()

    # Calculate approval rate
    approved_entries = work_entries.filter(review_status='approved').count()
    approval_rate = (approved_entries / total_entries * 100) if total_entries > 0 else 0

    # Calculate efficiency score
    planned_minutes = work_entries.aggregate(
        total=Sum('planned_minutes')
    )['total'] or 0
    efficiency_score = 0
    if planned_minutes > 0:
        efficiency_score = min(100, (total_minutes / planned_minutes) * 100)

    # Get daily hours distribution
    daily_hours = defaultdict(int)
    for entry in work_entries:
        if entry.actual_minutes:
            daily_hours[str(entry.date)] += entry.actual_minutes / 60

    # Generate labels for the period
    daily_labels = []
    daily_hours_data = []

    if period == 'week':
        # Get last 7 days
        for i in range(7):
            date = today - timedelta(days=6-i)
            daily_labels.append(date.strftime('%a'))
            daily_hours_data.append(round(daily_hours.get(str(date), 0), 1))
    elif period == 'month':
        # Get last 4 weeks
        for i in range(4):
            week_start = today - timedelta(days=(3-i)*7)
            daily_labels.append(f'Week {4-i}')
            week_total = sum(daily_hours.get(str(week_start + timedelta(days=d)), 0) for d in range(7))
            daily_hours_data.append(round(week_total, 1))
    elif period == 'quarter':
        # Get last 3 months
        for i in range(3):
            month_date = today.replace(month=(today.month - (2-i) - 1) % 12 + 1, day=1)
            month_name = month_date.strftime('%b')
            daily_labels.append(month_name)
    else:  # year
        # Get last 12 months
        for i in range(12):
            month_date = today.replace(month=(today.month - (11-i) - 1) % 12 + 1, day=1)
            month_name = month_date.strftime('%b')
            daily_labels.append(month_name)

    # Calculate utilization rate (8 hours work day)
    work_days = (today - start_date).days + 1
    target_hours = work_days * 8
    utilization_rate = min(100, (total_hours / target_hours * 100)) if target_hours > 0 else 0

    # Calculate completion rate
    completion_rate = (completed_entries / total_entries * 100) if total_entries > 0 else 0

    # Calculate on-time delivery (entries completed on or before planned time)
    on_time_entries = work_entries.filter(
        status='completed',
        actual_minutes__lte=F('planned_minutes')
    ).count()
    ontime_rate = (on_time_entries / completed_entries * 100) if completed_entries > 0 else 0

    # Calculate overall performance
    overall_performance = (utilization_rate + completion_rate + approval_rate + ontime_rate) / 4

    # Calculate changes (mock data for now, in real app would compare with previous period)
    hours_change = 12  # Mock: +12%
    tasks_change = 8   # Mock: +8%
    approval_change = 5  # Mock: +5%
    efficiency_change = -3  # Mock: -3%

    return Response({
        'total_hours': round(total_hours, 1),
        'completed_tasks': completed_entries,
        'approval_rate': round(approval_rate),
        'efficiency_score': round(efficiency_score),
        'hours_change': hours_change,
        'tasks_change': tasks_change,
        'approval_change': approval_change,
        'efficiency_change': efficiency_change,
        'daily_labels': daily_labels,
        'daily_hours': daily_hours_data,
        'task_status': {
            'completed': completed_entries,
            'in_progress': in_progress_entries,
            'pending': not_started_entries
        },
        'utilization_rate': round(utilization_rate),
        'completion_rate': round(completion_rate),
        'ontime_rate': round(ontime_rate),
        'overall_performance': round(overall_performance)
    })


# WORK ENTRIES - Employee spreadsheet
def _serialize_entry(e, include_employee_name=False):
    data = {
        'id': e.id,
        'date': str(e.date),
        'project_name': e.project_name,
        'task_done': e.task_done,
        'planned_minutes': e.planned_minutes,
        'start_time': e.start_time.isoformat() if e.start_time else None,
        'original_start_time': e.original_start_time.isoformat() if e.original_start_time else None,
        'end_time': e.end_time.isoformat() if e.end_time else None,
        'actual_minutes': e.actual_minutes,
        'status': e.status,
        'accumulated_minutes': e.accumulated_minutes,
        'pause_count': e.pause_count,
        'paused_at': e.paused_at.isoformat() if e.paused_at else None,
        'total_paused_seconds': e.total_paused_seconds,
        'remark': e.remark,
        'review_status': e.review_status,
        'admin_comment': e.admin_comment,
        'is_manual_entry': e.is_manual_entry,
        'is_reassigned': e.is_reassigned,
        'original_owner': e.original_owner.get_full_name() if e.original_owner else None,
        'reassigned_from': e.reassigned_from.get_full_name() if e.reassigned_from else None,
        'reassigned_to': e.reassigned_to.get_full_name() if e.reassigned_to else None,
        'reassigned_at': e.reassigned_at.isoformat() if e.reassigned_at else None,
    }
    if include_employee_name:
        data['employee_name'] = e.employee.get_full_name()
        data['employee_id'] = e.employee.id
    return data


# WORK ENTRIES - Employee spreadsheet
@api_view(['GET', 'POST'])
def work_entries_view(request):
    if request.method == 'GET':
        month = request.query_params.get('month')
        year = request.query_params.get('year')

        # Safety net: close out any timer the employee forgot to stop,
        # before returning entries.
        _auto_stop_overdue_entries(WorkEntry.objects.filter(employee=request.user))

        entries = WorkEntry.objects.filter(employee=request.user)

        if month and year:
            entries = entries.filter(date__month=month, date__year=year)

        entries = entries.order_by('-date', '-submitted_at')
        return Response([_serialize_entry(e) for e in entries])

    elif request.method == 'POST':
        from django.utils.dateparse import parse_datetime

        is_manual = bool(request.data.get('is_manual_entry', False))
        start_time = parse_datetime(request.data.get('start_time')) if request.data.get('start_time') else None
        end_time = parse_datetime(request.data.get('end_time')) if request.data.get('end_time') else None

        actual_minutes = request.data.get('actual_minutes')
        if actual_minutes is None and start_time and end_time:
            actual_minutes = round((end_time - start_time).total_seconds() / 60)

        entry = WorkEntry.objects.create(
            employee=request.user,
            date=request.data.get('date'),
            project_name=request.data.get('project_name'),
            task_done=request.data.get('task_done'),
            planned_minutes=request.data.get('planned_minutes', 0),
            status=request.data.get('status', 'not_started'),
            remark=request.data.get('remark', ''),
            is_manual_entry=is_manual,
            start_time=start_time,
            # A manual entry already has a real start time up front (there's
            # no separate "Start" click / resume cycle to worry about), so
            # original_start_time is simply the same value from creation.
            original_start_time=start_time,
            end_time=end_time,
            actual_minutes=actual_minutes,
            review_status='pending',
        )
        return Response(_serialize_entry(entry), status=201)


# WORK ENTRY DETAIL
@api_view(['PUT', 'DELETE'])
def work_entry_detail_view(request, pk):
    try:
        entry = WorkEntry.objects.get(pk=pk, employee=request.user)
    except WorkEntry.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)

    if request.method == 'PUT':
        entry.date = request.data.get('date', entry.date)
        entry.project_name = request.data.get('project_name', entry.project_name)
        entry.task_done = request.data.get('task_done', entry.task_done)
        entry.planned_minutes = request.data.get('planned_minutes', entry.planned_minutes)
        entry.remark = request.data.get('remark', entry.remark)

        # Timer-related fields — only update if explicitly sent
        from django.utils.dateparse import parse_datetime
        if 'start_time' in request.data:
            val = request.data.get('start_time')
            parsed = parse_datetime(val) if val else None
            entry.start_time = parsed
            # Only capture original_start_time the FIRST time this entry is
            # ever started (i.e. it hasn't been set yet). Every later
            # start_time write — resuming after a pause — must NOT touch it,
            # otherwise the "Start" column would keep jumping forward on
            # every resume, which is the exact bug being fixed here.
            if parsed and not entry.original_start_time:
                entry.original_start_time = parsed
        if 'end_time' in request.data:
            val = request.data.get('end_time')
            entry.end_time = parse_datetime(val) if val else None
        if 'actual_minutes' in request.data:
            entry.actual_minutes = request.data.get('actual_minutes')
        if 'status' in request.data:
            entry.status = request.data.get('status')
        if 'accumulated_minutes' in request.data:
            entry.accumulated_minutes = request.data.get('accumulated_minutes')
        if 'pause_count' in request.data:
            entry.pause_count = request.data.get('pause_count')
        if 'paused_at' in request.data:
            from django.utils.dateparse import parse_datetime as _parse_dt
            val = request.data.get('paused_at')
            entry.paused_at = _parse_dt(val) if val else None
        if 'total_paused_seconds' in request.data:
            entry.total_paused_seconds = request.data.get('total_paused_seconds')

        entry.save()
        return Response(_serialize_entry(entry))

    elif request.method == 'DELETE':
        entry.delete()
        return Response({'message': 'Deleted'})


# ADMIN - Get a single employee's work entries (company-scoped)
@api_view(['GET'])
def admin_employee_entries_view(request, employee_id):
    profile, err = get_admin_profile_or_403(request)
    if err:
        return err

    try:
        employee = User.objects.get(id=employee_id, employeeprofile__company=profile.company)
    except User.DoesNotExist:
        return Response({'error': 'Employee not found'}, status=404)

    month = request.query_params.get('month')
    year = request.query_params.get('year')

    # Safety net: close out any timer this employee forgot to stop,
    # before returning entries to the admin.
    _auto_stop_overdue_entries(WorkEntry.objects.filter(employee=employee))

    entries = WorkEntry.objects.filter(employee=employee)

    if month and year:
        entries = entries.filter(date__month=month, date__year=year)

    entries = entries.order_by('-date', '-submitted_at')
    return Response([_serialize_entry(e, include_employee_name=True) for e in entries])


# ADMIN - Review entry (company-scoped)
@api_view(['PUT'])
def admin_review_entry_view(request, pk):
    profile, err = get_admin_profile_or_403(request)
    if err:
        return err

    try:
        entry = WorkEntry.objects.get(pk=pk, employee__employeeprofile__company=profile.company)
    except WorkEntry.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)

    entry.review_status = request.data.get('review_status', entry.review_status)
    entry.admin_comment = request.data.get('admin_comment', entry.admin_comment)
    entry.save()
    return Response(_serialize_entry(entry))


# ADMIN - Pause / resume an entry (company-scoped)
@api_view(['PUT'])
def admin_pause_entry_view(request, pk):
    profile, err = get_admin_profile_or_403(request)
    if err:
        return err

    try:
        entry = WorkEntry.objects.get(pk=pk, employee__employeeprofile__company=profile.company)
    except WorkEntry.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)

    action = request.data.get('action')

    if action == 'pause':
        if entry.status != 'in_progress':
            return Response({'error': 'Entry is not in progress'}, status=400)
        from django.utils import timezone
        if entry.start_time:
            elapsed = (timezone.now() - entry.start_time).total_seconds() / 60
            entry.accumulated_minutes = (entry.accumulated_minutes or 0) + round(elapsed)
        entry.pause_count = (entry.pause_count or 0) + 1
        # Mark exactly when this pause began so the frontend can render a
        # live, ticking "paused for..." counter that keeps counting until
        # resume — independent of the (now-frozen) work-time timer above.
        entry.paused_at = timezone.now()
        entry.status = 'paused'
        entry.save()
    elif action == 'resume':
        if entry.status != 'paused':
            return Response({'error': 'Entry is not paused'}, status=400)
        from django.utils import timezone
        # Fold this pause's duration into the running total (across every
        # pause on this entry) before clearing paused_at, so a later pause
        # continues accumulating rather than starting over from zero.
        if entry.paused_at:
            paused_seconds = (timezone.now() - entry.paused_at).total_seconds()
            entry.total_paused_seconds = (entry.total_paused_seconds or 0) + round(paused_seconds)
        entry.paused_at = None
        # NOTE: start_time is intentionally reset to "now" here — it's used
        # to measure THIS work session's elapsed time. original_start_time
        # is deliberately left untouched (it was already set on the very
        # first Start and should keep reflecting that).
        entry.start_time = timezone.now()
        entry.status = 'in_progress'
        entry.save()
    else:
        return Response({'error': 'action must be "pause" or "resume"'}, status=400)

    return Response(_serialize_entry(entry))


# ADMIN - All reports (company-scoped)
@api_view(['GET'])
def admin_all_reports_view(request):
    profile, err = get_admin_profile_or_403(request)
    if err:
        return err

    reports = DailyReport.objects.filter(employee__employeeprofile__company=profile.company)
    status_filter = request.query_params.get('status')
    if status_filter:
        reports = reports.filter(status=status_filter)
    search = request.query_params.get('search')
    if search:
        reports = reports.filter(employee__first_name__icontains=search) | \
                  reports.filter(employee__last_name__icontains=search)
    serializer = DailyReportSerializer(reports, many=True)
    return Response(serializer.data)


# ADMIN - Review report (company-scoped)
@api_view(['PUT'])
def admin_review_report_view(request, pk):
    profile, err = get_admin_profile_or_403(request)
    if err:
        return err

    try:
        report = DailyReport.objects.get(pk=pk, employee__employeeprofile__company=profile.company)
    except DailyReport.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)

    report.status = request.data.get('status', report.status)
    report.manager_comment = request.data.get('manager_comment', report.manager_comment)
    report.save()
    return Response(DailyReportSerializer(report).data)


# ADMIN - All employees (company-scoped) — THE FIX
@api_view(['GET'])
def admin_employees_view(request):
    profile, err = get_admin_profile_or_403(request)
    if err:
        return err

    users = User.objects.filter(
        employeeprofile__is_admin=False,
        employeeprofile__company=profile.company
    )
    serializer = UserSerializer(users, many=True, context={'request': request})
    return Response(serializer.data)


# ADMIN - Dashboard stats (company-scoped)
@api_view(['GET'])
def admin_stats_view(request):
    profile, err = get_admin_profile_or_403(request)
    if err:
        return err

    reports = DailyReport.objects.filter(employee__employeeprofile__company=profile.company)
    return Response({
        'total_employees': User.objects.filter(
            employeeprofile__is_admin=False, employeeprofile__company=profile.company
        ).count(),
        'total_reports': reports.count(),
        'pending_review': reports.filter(status='pending').count(),
        'approved': reports.filter(status='approved').count(),
        'rejected': reports.filter(status='rejected').count(),
        'approval_rate': round(
            reports.filter(status='approved').count() / max(reports.count(), 1) * 100
        ),
        'recent_reports': DailyReportSerializer(reports[:6], many=True).data
    })


# ADMIN - Analytics data (company-scoped)
@api_view(['GET'])
def admin_analytics_view(request):
    """Get comprehensive analytics data for the admin dashboard"""
    profile, err = get_admin_profile_or_403(request)
    if err:
        return err

    company = profile.company

    # Get all employees in the company (excluding admins)
    employees = User.objects.filter(
        employeeprofile__company=company,
        employeeprofile__is_admin=False
    )

    # Get work entries for the company
    from django.db.models import Sum, Q, F, Case, When
    from django.utils import timezone
    from datetime import timedelta, datetime

    # Get the period filter (default to this month)
    period = request.query_params.get('period', 'month')
    today = timezone.now().date()

    if period == 'week':
        start_date = today - timedelta(days=today.weekday())
    elif period == 'quarter':
        start_date = today.replace(month=(today.month - 3) % 12 + 1, day=1)
    elif period == 'year':
        start_date = today.replace(month=1, day=1)
    else:  # month
        start_date = today.replace(day=1)

    # Get work entries for the period
    work_entries = WorkEntry.objects.filter(
        employee__employeeprofile__company=company,
        date__gte=start_date,
        date__lte=today
    )

    # Calculate total hours
    total_minutes = work_entries.aggregate(
        total=Sum('actual_minutes')
    )['total'] or 0
    total_hours = total_minutes / 60

    # Calculate tasks completed (based on work entries with status)
    total_entries = work_entries.count()
    completed_entries = work_entries.filter(status='completed').count()
    in_progress_entries = work_entries.filter(status='in_progress').count()
    not_started_entries = work_entries.filter(status='not_started').count()

    # Calculate pending reviews (entries awaiting admin review)
    pending_review = work_entries.filter(review_status='pending').count()

    # Calculate average hours per day
    distinct_days = work_entries.values('date').distinct().count()
    avg_per_day = round(total_hours / max(distinct_days, 1), 1) if distinct_days > 0 else 0

    # Calculate completion rate
    completion_rate = round((completed_entries / max(total_entries, 1)) * 100) if total_entries > 0 else 0

    # Calculate utilization (actual hours / (8 hours * working days))
    target_hours = 8 * distinct_days  # 8 hours per working day
    utilization_rate = round((total_hours / max(target_hours, 1)) * 100) if target_hours > 0 else 0

    # Calculate approval rate
    approved_entries = work_entries.filter(review_status='approved').count()
    approval_rate = round((approved_entries / max(total_entries, 1)) * 100) if total_entries > 0 else 0

    # Get hours by employee
    hours_by_employee = []
    for emp in employees[:5]:  # Top 5 employees
        emp_entries = work_entries.filter(employee=emp)
        emp_total = emp_entries.aggregate(total=Sum('actual_minutes'))['total'] or 0
        emp_hours = emp_total / 60
        emp_tasks = emp_entries.filter(status='completed').count()
        hours_by_employee.append({
            'id': emp.id,
            'name': f"{emp.first_name} {emp.last_name}",
            'hours': round(emp_hours, 1),
            'tasks': emp_tasks,
            'initials': f"{emp.first_name[0]}{emp.last_name[0]}" if emp.last_name else emp.first_name[0]
        })

    # Sort by hours
    hours_by_employee.sort(key=lambda x: x['hours'], reverse=True)

    # Get tasks by department
    departments = EmployeeProfile.objects.filter(
        company=company,
        is_admin=False
    ).values('department').annotate(
        count=Count('user_id')
    ).filter(count__gt=0)

    tasks_by_department = []
    for dept in departments:
        dept_employees = employees.filter(
            employeeprofile__department=dept['department']
        )
        dept_entries = work_entries.filter(employee__in=dept_employees)
        dept_tasks = dept_entries.filter(status='completed').count()
        total_dept_entries = dept_entries.count()
        tasks_by_department.append({
            'name': dept['department'] or 'Unassigned',
            'tasks': dept_tasks,
            'total': total_dept_entries,
            'progress': round((dept_tasks / max(total_dept_entries, 1)) * 100) if total_dept_entries > 0 else 0
        })

    # Sort by tasks
    tasks_by_department.sort(key=lambda x: x['tasks'], reverse=True)

    # Weekly trend (last 7 days)
    weekly_trend = []
    for i in range(7):
        date = today - timedelta(days=6-i)
        day_entries = work_entries.filter(date=date)
        day_total = day_entries.aggregate(total=Sum('actual_minutes'))['total'] or 0
        weekly_trend.append({
            'date': date.strftime('%Y-%m-%d'),
            'hours': round(day_total / 60, 1),
            'day': date.strftime('%a')[:3]  # Mon, Tue, etc.
        })

    # Get top performers
    top_performers = []
    for emp in employees:
        emp_entries = work_entries.filter(employee=emp)
        emp_total = emp_entries.aggregate(total=Sum('actual_minutes'))['total'] or 0
        emp_hours = emp_total / 60
        emp_tasks = emp_entries.filter(status='completed').count()
        emp_total_entries = emp_entries.count()
        emp_efficiency = round((emp_tasks / max(emp_total_entries, 1)) * 100) if emp_total_entries > 0 else 0

        if emp_total_entries > 0:  # Only include if they have entries
            top_performers.append({
                'id': emp.id,
                'name': f"{emp.first_name} {emp.last_name}",
                'department': emp.employeeprofile.department if hasattr(emp, 'employeeprofile') else 'N/A',
                'hours': round(emp_hours, 1),
                'tasks': emp_tasks,
                'efficiency': emp_efficiency
            })

    # Sort by efficiency and take top 5
    top_performers.sort(key=lambda x: x['efficiency'], reverse=True)
    top_performers = top_performers[:5]

    return Response({
        'totalHours': round(total_hours),
        'tasksCompleted': completed_entries,
        'avgPerDay': avg_per_day,
        'pendingReview': pending_review,
        'completionRate': completion_rate,
        'activeHours': round(total_hours / max(distinct_days, 1), 1) if distinct_days > 0 else 0,
        'teamUtilization': utilization_rate,
        'hoursByEmployee': hours_by_employee,
        'tasksByDepartment': tasks_by_department,
        'weeklyTrend': weekly_trend,
        'topPerformers': top_performers,
        'employees': [
            {
                'id': emp.id,
                'name': f"{emp.first_name} {emp.last_name}",
                'initials': f"{emp.first_name[0]}{emp.last_name[0]}" if emp.last_name else emp.first_name[0]
            }
            for emp in employees
        ]
    })


def _serialize_task(t):
    return {
        'id': t.id,
        'project_name': t.project_name,
        'task_description': t.task_description,
        'deadline': str(t.deadline) if t.deadline else '',
        'planned_minutes': t.planned_minutes,
        'start_time': t.start_time.isoformat() if t.start_time else None,
        'end_time': t.end_time.isoformat() if t.end_time else None,
        'actual_minutes': t.actual_minutes,
        'status': t.status,
        'assigned_to': t.assigned_to.get_full_name(),
        'assigned_to_id': t.assigned_to.id,
        'assigned_by': t.assigned_by.get_full_name(),
        'is_reassigned': t.is_reassigned,
        'original_owner': t.original_owner.get_full_name() if t.original_owner else None,
        'reassigned_from': t.reassigned_from.get_full_name() if t.reassigned_from else None,
        'reassigned_to': t.reassigned_to.get_full_name() if t.reassigned_to else None,
        'reassigned_at': t.reassigned_at.isoformat() if t.reassigned_at else None,
    }


# ADMIN - Assign task (company-scoped)
@api_view(['GET', 'POST'])
def assign_task_view(request):
    profile, err = get_admin_profile_or_403(request)
    if err:
        return err

    if request.method == 'GET':
        tasks = AssignedTask.objects.filter(assigned_by=request.user)
        return Response([_serialize_task(t) for t in tasks])

    elif request.method == 'POST':
        try:
            employee = User.objects.get(
                id=request.data.get('employee_id'),
                employeeprofile__company=profile.company
            )
        except User.DoesNotExist:
            return Response({'error': 'Employee not found'}, status=404)

        task = AssignedTask.objects.create(
            assigned_to=employee,
            assigned_by=request.user,
            project_name=request.data.get('project_name'),
            task_description=request.data.get('task_description'),
            deadline=request.data.get('deadline') or None,
            planned_minutes=request.data.get('planned_minutes', 0),
        )
        return Response(_serialize_task(task), status=201)


# EMPLOYEE - Get assigned tasks
@api_view(['GET'])
def employee_assigned_tasks_view(request):
    tasks = AssignedTask.objects.filter(assigned_to=request.user)
    return Response([_serialize_task(t) for t in tasks])


# EMPLOYEE - Start / Complete an assigned task
@api_view(['PUT'])
def assigned_task_action_view(request, pk):
    try:
        task = AssignedTask.objects.get(pk=pk, assigned_to=request.user)
    except AssignedTask.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)

    action = request.data.get('action')  # 'start' or 'complete'

    if action == 'start':
        task.start_time = timezone.now()
        task.status = 'in_progress'
        task.save()

    elif action == 'complete':
        if not task.start_time:
            return Response({'error': 'Task was never started'}, status=400)
        task.end_time = timezone.now()
        task.actual_minutes = round((task.end_time - task.start_time).total_seconds() / 60)
        task.status = 'completed'
        task.save()

    else:
        return Response({'error': 'Invalid action'}, status=400)

    return Response(_serialize_task(task))

# UPDATE PROFILE
@api_view(['PUT'])
def update_profile_view(request):
    user = request.user
    user.first_name = request.data.get('first_name', user.first_name)
    user.last_name = request.data.get('last_name', user.last_name)
    user.save()

    try:
        profile = user.employeeprofile
        profile.phone = request.data.get('phone', profile.phone)
        profile.department = request.data.get('department', profile.department)
        profile.designation = request.data.get('designation', profile.designation)

        # The frontend sends the file under the key 'profile_picture'
        # (see profile.html's handleEditSubmit: formData.append('profile_picture', ...)).
        # The model field itself is still called `photo` — only the upload
        # field name from the form was mismatched, not the DB column.
        uploaded_photo = request.FILES.get('profile_picture') or request.FILES.get('photo')
        # 'remove_photo' comes from the profile page's dedicated Remove
        # Photo button (sent as a plain form field, not a file). It's
        # checked before a new upload so the two can't conflict, but in
        # practice the frontend only ever sends one or the other in a
        # given request.
        remove_photo = str(request.data.get('remove_photo', '')).lower() in ('true', '1', 'yes')
        if remove_photo and profile.photo:
            profile.photo.delete(save=False)
            profile.photo = None
        elif uploaded_photo:
            profile.photo = uploaded_photo

        profile.save()
        profile.refresh_from_db()

        photo_url = None
        photo = getattr(profile, 'photo', None)
        if photo:
            try:
                photo_url = request.build_absolute_uri(photo.url)
            except Exception:
                photo_url = None

    except Exception as e:
        print(f'Profile update error: {e}')
        profile = None
        photo_url = None

    return Response({
        'id': user.id,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'full_name': user.get_full_name(),
        'profile': {
            'employee_id': profile.employee_id if profile else '',
            'department': profile.department if profile else '',
            'designation': profile.designation if profile else '',
            'phone': profile.phone if profile else '',
            'is_admin': profile.is_admin if profile else False,
            'photo': photo_url,
        }
    })


# DELETE EMPLOYEE (company-scoped — can't delete someone from another company)
@api_view(['DELETE'])
def delete_employee_view(request, employee_id):
    profile, err = get_admin_profile_or_403(request)
    if err:
        return err

    try:
        employee = User.objects.get(id=employee_id, employeeprofile__company=profile.company)
        employee.delete()
        return Response({'message': 'Employee deleted'})
    except User.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)


@api_view(['POST'])
def change_password_view(request):
    user = request.user
    current_password = request.data.get('current_password')
    new_password = request.data.get('new_password')

    if not user.check_password(current_password):
        return Response({'error': 'Current password is incorrect.'}, status=400)

    password_error = validate_password_strength(new_password)
    if password_error:
        return Response({'error': password_error}, status=400)

    user.set_password(new_password)
    user.save()
    # Re-create token so existing sessions are invalidated
    Token.objects.filter(user=user).delete()
    token = Token.objects.create(user=user)
    return Response({'message': 'Password updated successfully.', 'token': token.key})


# ── REASSIGN WORK ENTRY ──────────────────────────────────────────────
@api_view(['POST'])
def reassign_work_entry_view(request, pk):
    """
    Reassigning a WorkEntry does NOT move it — it creates a new entry
    for the target employee and freezes the original in place.
    """
    try:
        entry = WorkEntry.objects.get(pk=pk)
    except WorkEntry.DoesNotExist:
        return Response({'error': 'Work entry not found'}, status=404)

    try:
        requester_profile = request.user.employeeprofile
        is_admin = requester_profile.is_admin
    except:
        requester_profile = None
        is_admin = False

    if not is_admin and entry.employee != request.user:
        return Response({'error': 'You can only reassign your own entries'}, status=403)

    if entry.reassigned_to_id:
        return Response({'error': 'This entry has already been reassigned'}, status=400)

    to_employee_id = request.data.get('to_employee_id')
    if not to_employee_id:
        return Response({'error': 'to_employee_id is required'}, status=400)

    try:
        to_employee = User.objects.get(id=to_employee_id)
    except User.DoesNotExist:
        return Response({'error': 'Target employee not found'}, status=404)

    # Prevent reassigning across companies
    try:
        entry_company = entry.employee.employeeprofile.company
        target_company = to_employee.employeeprofile.company
        if entry_company != target_company:
            return Response({'error': 'Cannot reassign to an employee outside your company'}, status=403)
    except EmployeeProfile.DoesNotExist:
        return Response({'error': 'Target employee not found'}, status=404)

    if to_employee == entry.employee:
        return Response({'error': 'Cannot reassign to the same employee'}, status=400)

    from_employee = entry.employee
    original_owner = entry.original_owner or from_employee

    new_entry = WorkEntry.objects.create(
        employee=to_employee,
        date=entry.date,
        project_name=entry.project_name,
        task_done=entry.task_done,
        planned_minutes=entry.planned_minutes,
        status='not_started',
        remark=entry.remark,
        original_owner=original_owner,
        is_reassigned=True,
        reassigned_from=from_employee,
        reassigned_at=timezone.now(),
        reassigned_by_admin=request.user if is_admin else None,
    )
    # Stop the timer if it was running, and freeze the entry
    if entry.status == 'in_progress' and entry.start_time:
        now = timezone.now()
        entry.end_time = now
        entry.actual_minutes = round((now - entry.start_time).total_seconds() / 60)

    entry.status = 'reassigned'
    entry.is_reassigned = True
    entry.original_owner = original_owner
    entry.reassigned_to = to_employee
    entry.reassigned_at = timezone.now()
    entry.reassigned_by_admin = request.user if is_admin else None
    entry.save()

    ReassignmentLog.objects.create(
        item_type='work_entry',
        item_id=entry.id,
        from_employee=from_employee,
        to_employee=to_employee,
        reassigned_by=request.user,
        note=request.data.get('note', '')
    )

    return Response(_serialize_entry(entry))


# ── REASSIGN ASSIGNED TASK ───────────────────────────────────────────
@api_view(['POST'])
def reassign_assigned_task_view(request, pk):
    """
    Any authenticated user (employee or admin) can reassign an AssignedTask.
    Body: { "to_employee_id": <int> }
    """
    try:
        task = AssignedTask.objects.get(pk=pk)
    except AssignedTask.DoesNotExist:
        return Response({'error': 'Task not found'}, status=404)

    try:
        is_admin = request.user.employeeprofile.is_admin
    except:
        is_admin = False

    if not is_admin and task.assigned_to != request.user:
        return Response({'error': 'You can only reassign your own tasks'}, status=403)

    to_employee_id = request.data.get('to_employee_id')
    if not to_employee_id:
        return Response({'error': 'to_employee_id is required'}, status=400)

    try:
        to_employee = User.objects.get(id=to_employee_id)
    except User.DoesNotExist:
        return Response({'error': 'Target employee not found'}, status=404)

    # Prevent reassigning across companies
    try:
        task_company = task.assigned_to.employeeprofile.company
        target_company = to_employee.employeeprofile.company
        if task_company != target_company:
            return Response({'error': 'Cannot reassign to an employee outside your company'}, status=403)
    except EmployeeProfile.DoesNotExist:
        return Response({'error': 'Target employee not found'}, status=404)

    if to_employee == task.assigned_to:
        return Response({'error': 'Cannot reassign to the same employee'}, status=400)

    from_employee = task.assigned_to

    if not task.is_reassigned:
        task.original_owner = from_employee

    ReassignmentLog.objects.create(
        item_type='assigned_task',
        item_id=task.id,
        from_employee=from_employee,
        to_employee=to_employee,
        reassigned_by=request.user,
        note=request.data.get('note', '')
    )

    task.assigned_to = to_employee
    task.is_reassigned = True
    task.reassigned_from = from_employee
    task.reassigned_to = to_employee
    task.reassigned_at = timezone.now()
    task.reassigned_by_admin = request.user if is_admin else None

    task.status = 'assigned'
    task.start_time = None
    task.end_time = None
    task.actual_minutes = None

    task.save()
    return Response(_serialize_task(task))


# ── LIST ALL EMPLOYEES (for reassign modal) — company-scoped ─────────
@api_view(['GET'])
def all_employees_for_reassign_view(request):
    """
    Returns all non-admin employees in the requester's own company,
    with photo URLs. Used to populate the reassign modal.
    """
    try:
        requester_profile = request.user.employeeprofile
    except EmployeeProfile.DoesNotExist:
        return Response([])

    users = User.objects.filter(
        employeeprofile__is_admin=False,
        employeeprofile__company=requester_profile.company
    ).select_related('employeeprofile')

    data = []
    for u in users:
        try:
            profile = u.employeeprofile
            photo_url = None
            if getattr(profile, 'photo', None):
                try:
                    photo_url = request.build_absolute_uri(profile.photo.url)
                except:
                    photo_url = None
            data.append({
                'id': u.id,
                'full_name': u.get_full_name() or u.email,
                'email': u.email,
                'department': profile.department,
                'designation': profile.designation,
                'photo': photo_url,
            })
        except:
            pass
    return Response(data)


ONLINE_THRESHOLD_SECONDS = 60


def _is_online(profile):
    """A user counts as 'online' if their last heartbeat was within the
    last ONLINE_THRESHOLD_SECONDS — the frontend pings /api/heartbeat/
    every ~20s while a WorkTrack tab is open and active."""
    if not profile or not profile.last_active:
        return False
    return (timezone.now() - profile.last_active).total_seconds() < ONLINE_THRESHOLD_SECONDS


@api_view(['POST'])
def heartbeat_view(request):
    try:
        profile = request.user.employeeprofile
        profile.last_active = timezone.now()
        profile.save(update_fields=['last_active'])
    except EmployeeProfile.DoesNotExist:
        pass
    return Response({'ok': True})


@api_view(['GET'])
def user_status_view(request, user_id):
    try:
        u = User.objects.get(id=user_id)
        profile = u.employeeprofile
        return Response({'online': _is_online(profile)})
    except (User.DoesNotExist, EmployeeProfile.DoesNotExist):
        return Response({'online': False})


def _serialize_message(msg, viewer=None):
    try:
        profile = msg.sender.employeeprofile
        photo_url = None
        if getattr(profile, 'photo', None):
            try:
                photo_url = f'http://127.0.0.1:8001{profile.photo.url}'
            except:
                pass
        is_admin = profile.is_admin
    except:
        photo_url = None
        is_admin = False

    # "Delete for everyone": content/attachment were cleared server-side
    # when the sender deleted it — show a placeholder to every viewer.
    if msg.is_deleted_for_everyone:
        return {
            'id': msg.id,
            'content': '',
            'sender_id': msg.sender.id,
            'sender_name': msg.sender.get_full_name() or msg.sender.email,
            'sender_photo': photo_url,
            'is_admin': is_admin,
            'created_at': msg.created_at.isoformat(),
            'room_id': msg.room.id,
            'attachment_url': None,
            'attachment_name': '',
            'is_deleted_for_everyone': True,
        }

    attachment_url = None
    if msg.attachment:
        try:
            attachment_url = f'http://127.0.0.1:8001{msg.attachment.url}'
        except:
            pass

    return {
        'id': msg.id,
        'content': msg.content,
        'sender_id': msg.sender.id,
        'sender_name': msg.sender.get_full_name() or msg.sender.email,
        'sender_photo': photo_url,
        'is_admin': is_admin,
        'created_at': msg.created_at.isoformat(),
        'room_id': msg.room.id,
        'attachment_url': attachment_url,
        'attachment_name': msg.attachment_name or '',
        'is_deleted_for_everyone': False,
    }



def _get_or_create_group_room(company):
    room, created = ChatRoom.objects.get_or_create(
        name='Team Chat', room_type='group', company=company,
        defaults={'is_default_group': True},
    )
    if created:
        for user in User.objects.filter(employeeprofile__company=company, employeeprofile__is_admin=False):
            room.participants.add(user)
    else:
        if not room.is_default_group:
            room.is_default_group = True
            room.save(update_fields=['is_default_group'])
        admins_in_room = room.participants.filter(employeeprofile__is_admin=True)
        if admins_in_room.exists():
            room.participants.remove(*admins_in_room)
    return room

@api_view(['GET'])
def chat_rooms_view(request):
    try:
        requester_profile = request.user.employeeprofile
    except EmployeeProfile.DoesNotExist:
        return Response([])

    group_room = _get_or_create_group_room(requester_profile.company)
    # Admins never join the employees-only Team Chat.
    if not requester_profile.is_admin:
        group_room.participants.add(request.user)
    rooms = request.user.chat_rooms.all().order_by('-created_at')
    data = []
    for room in rooms:
        last_msg = room.messages.last()
        if room.room_type == 'direct':
            other = room.participants.exclude(id=request.user.id).first()
            if not other:
                continue
            try:
                profile = other.employeeprofile
                photo_url = f'http://127.0.0.1:8001{profile.photo.url}' if getattr(profile, 'photo', None) else None
                online = _is_online(profile)
            except:
                photo_url = None
                online = False
            data.append({
                'id': room.id,
                'name': other.get_full_name() or other.email,
                'room_type': 'direct',
                'other_user_id': other.id,
                'other_user_photo': photo_url,
                'other_user_online': online,
                'last_message': last_msg.content if (last_msg and not last_msg.is_deleted_for_everyone) else ('This message was deleted' if last_msg else ''),
                'last_message_time': last_msg.created_at.isoformat() if last_msg else '',
            })
        else:
            data.append({
                'id': room.id,
                'name': room.name,
                'room_type': 'group',
                'participant_count': room.participants.count(),
                'is_default_group': room.is_default_group,
                'last_message': last_msg.content if (last_msg and not last_msg.is_deleted_for_everyone) else ('This message was deleted' if last_msg else ''),
                'last_message_time': last_msg.created_at.isoformat() if last_msg else '',
            })
    return Response(data)


@api_view(['POST'])
def create_dm_room_view(request):
    other_user_id = request.data.get('other_user_id')
    if not other_user_id:
        return Response({'error': 'other_user_id required'}, status=400)
    try:
        other_user = User.objects.get(id=other_user_id)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)

    # Prevent DMs across companies
    try:
        requester_company = request.user.employeeprofile.company
        other_company = other_user.employeeprofile.company
        if requester_company != other_company:
            return Response({'error': 'Cannot message users outside your company'}, status=403)
    except EmployeeProfile.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)

    existing = ChatRoom.objects.filter(room_type='direct', participants=request.user).filter(participants=other_user)
    if existing.exists():
        room = existing.first()
    else:
        room = ChatRoom.objects.create(room_type='direct', created_by=request.user)
        room.participants.add(request.user, other_user)
    last_msg = room.messages.last()
    try:
        profile = other_user.employeeprofile
        photo_url = f'http://127.0.0.1:8001{profile.photo.url}' if getattr(profile, 'photo', None) else None
    except:
        photo_url = None
    return Response({
        'id': room.id,
        'name': other_user.get_full_name() or other_user.email,
        'room_type': 'direct',
        'other_user_id': other_user.id,
        'other_user_photo': photo_url,
        'last_message': last_msg.content if last_msg else '',
        'last_message_time': last_msg.created_at.isoformat() if last_msg else '',
    }, status=201)
@api_view(['POST'])
def create_group_room_view(request):
    try:
        requester_profile = request.user.employeeprofile
    except EmployeeProfile.DoesNotExist:
        return Response({'error': 'Profile not found'}, status=404)

    # Admins can never create or belong to employee groups.
    if requester_profile.is_admin:
        return Response({'error': 'Admins cannot create or join employee groups'}, status=403)

    name = (request.data.get('name') or '').strip()
    member_ids = request.data.get('member_ids', [])

    if not name:
        return Response({'error': 'Group name is required'}, status=400)
    if not isinstance(member_ids, list) or not member_ids:
        return Response({'error': 'Select at least one teammate'}, status=400)

    # Server-side enforcement: only non-admin employees from the same
    # company can ever be added, regardless of what the client sends.
    members = User.objects.filter(
        id__in=member_ids,
        employeeprofile__company=requester_profile.company,
        employeeprofile__is_admin=False,
    ).exclude(id=request.user.id)

    if not members.exists():
        return Response({'error': 'No valid teammates selected'}, status=400)

    room = ChatRoom.objects.create(
        name=name,
        room_type='group',
        company=requester_profile.company,
        created_by=request.user,
        is_default_group=False,
    )
    room.participants.add(request.user, *members)

    return Response({
        'id': room.id,
        'name': room.name,
        'room_type': 'group',
        'participant_count': room.participants.count(),
        'is_default_group': False,
        'last_message': '',
        'last_message_time': '',
    }, status=201)

@api_view(['GET', 'POST'])
def chat_messages_view(request, room_id):
    try:
        room = ChatRoom.objects.get(id=room_id, participants=request.user)
    except ChatRoom.DoesNotExist:
        return Response({'error': 'Room not found'}, status=404)

    if request.method == 'GET':
        since = request.query_params.get('since')
        messages = room.messages.exclude(deleted_for=request.user)
        if since:
            try:
                from datetime import datetime
                since_dt = datetime.fromisoformat(since.replace('Z', '+00:00'))
                messages = messages.filter(created_at__gt=since_dt)
            except:
                pass
        messages = messages.order_by('created_at')[:100]
        return Response([_serialize_message(m, viewer=request.user) for m in messages])

    elif request.method == 'POST':
        # Handle both JSON and multipart (file upload)
        content = request.data.get('content', '').strip()
        attachment = request.FILES.get('attachment')

        if not content and not attachment:
            return Response({'error': 'Content or attachment required'}, status=400)

        if attachment and attachment.size > 25 * 1024 * 1024:
            return Response({'error': 'File is too large. Max size is 25MB.'}, status=400)
        if room.room_type == 'group' and room.is_default_group:
            try:
                company = request.user.employeeprofile.company
                for user in User.objects.filter(employeeprofile__company=company, employeeprofile__is_admin=False):
                    room.participants.add(user)
            except EmployeeProfile.DoesNotExist:
                pass

        msg = ChatMessage(room=room, sender=request.user, content=content)
        if attachment:
            msg.attachment = attachment
            msg.attachment_name = attachment.name
        msg.save()

        return Response(_serialize_message(msg, viewer=request.user), status=201)


@api_view(['GET'])
def all_users_for_chat_view(request):
    try:
        requester_profile = request.user.employeeprofile
    except EmployeeProfile.DoesNotExist:
        return Response([])

    users = User.objects.exclude(id=request.user.id).filter(
        employeeprofile__company=requester_profile.company
    ).select_related('employeeprofile')

    data = []
    for u in users:
        try:
            profile = u.employeeprofile
            photo_url = f'http://127.0.0.1:8001{profile.photo.url}' if getattr(profile, 'photo', None) else None
            data.append({
                'id': u.id,
                'full_name': u.get_full_name() or u.email,
                'email': u.email,
                'department': profile.department,
                'designation': profile.designation,
                'is_admin': profile.is_admin,
                'photo': photo_url,
            })
        except:
            pass
    return Response(data)


# ── RECENT MESSAGES ACROSS ALL ROOMS (for notifications) ──────────────
@api_view(['GET'])
def recent_messages_view(request):
    """
    Returns messages sent by OTHERS across all the user's rooms since `since`.
    Used to trigger notification popups.
    """
    since = request.query_params.get('since')
    rooms = request.user.chat_rooms.all()

    messages = ChatMessage.objects.filter(room__in=rooms).exclude(sender=request.user).exclude(deleted_for=request.user).exclude(is_deleted_for_everyone=True)

    if since:
        try:
            from datetime import datetime
            since_dt = datetime.fromisoformat(since.replace('Z', '+00:00'))
            messages = messages.filter(created_at__gt=since_dt)
        except:
            pass
    else:
        # First check ever — don't flood with old messages, just mark "now"
        return Response([])

    messages = messages.order_by('created_at')[:20]
    return Response([_serialize_message(m) for m in messages])


# ── UNREAD CHAT COUNT ─────────────────────────────────────────────────
@api_view(['GET'])
def unread_chat_count_view(request):
    rooms = request.user.chat_rooms.all()
    total_unread = 0
    per_room = {}

    for room in rooms:
        try:
            read_status = ChatReadStatus.objects.get(room=room, user=request.user)
            last_read = read_status.last_read_at
        except ChatReadStatus.DoesNotExist:
            last_read = None

        unread_qs = room.messages.exclude(sender=request.user).exclude(deleted_for=request.user)
        if last_read:
            unread_qs = unread_qs.filter(created_at__gt=last_read)

        count = unread_qs.count()
        if count > 0:
            per_room[room.id] = count
            total_unread += count

    return Response({'total_unread': total_unread, 'per_room': per_room})


# ── MARK ROOM AS READ ─────────────────────────────────────────────────
@api_view(['POST'])
def mark_room_read_view(request, room_id):
    try:
        room = ChatRoom.objects.get(id=room_id, participants=request.user)
    except ChatRoom.DoesNotExist:
        return Response({'error': 'Room not found'}, status=404)

    ChatReadStatus.objects.update_or_create(
        room=room, user=request.user,
        defaults={'last_read_at': timezone.now()}
    )
    return Response({'message': 'marked read'})
@api_view(['GET'])
def chat_room_read_status_view(request, room_id):
    """
    Returns when every OTHER participant in this room last read it,
    so the sender can show single-check (sent) vs blue double-check (seen).
    """
    try:
        room = ChatRoom.objects.get(id=room_id, participants=request.user)
    except ChatRoom.DoesNotExist:
        return Response({'error': 'Room not found'}, status=404)

    statuses = ChatReadStatus.objects.filter(room=room).exclude(user=request.user)
    data = [{'user_id': s.user_id, 'last_read_at': s.last_read_at.isoformat()} for s in statuses]
    return Response(data)

@api_view(['DELETE'])
def delete_chat_room_view(request, room_id):
    try:
        room = ChatRoom.objects.get(id=room_id, participants=request.user)
    except ChatRoom.DoesNotExist:
        return Response({'error': 'Room not found'}, status=404)

    if room.room_type == 'group':
        if room.is_default_group:
            return Response({'error': 'Cannot leave the company Team Chat'}, status=400)
        room.participants.remove(request.user)
        ChatReadStatus.objects.filter(room=room, user=request.user).delete()
        return Response({'message': 'Left group'})

    room.participants.remove(request.user)
    ChatReadStatus.objects.filter(room=room, user=request.user).delete()
    return Response({'message': 'Chat deleted'})

# ── DELETE CHAT MESSAGE ────────────────────────────────────────────────
@api_view(['DELETE'])
def delete_chat_message_view(request, message_id):
    try:
        msg = ChatMessage.objects.get(id=message_id)
    except ChatMessage.DoesNotExist:
        return Response({'error': 'Message not found'}, status=404)

    if request.user not in msg.room.participants.all():
        return Response({'error': 'Not a participant of this conversation'}, status=403)

    mode = request.query_params.get('mode', 'me')  # 'me' or 'everyone'

    if mode == 'everyone':
        # Only the original sender can delete for everyone — matches
        # WhatsApp behavior. Admins do not get a special override here;
        # deleting someone else's message is always "for me" only.
        if msg.sender != request.user:
            return Response({'error': 'You can only delete your own messages for everyone'}, status=403)
        msg.is_deleted_for_everyone = True
        msg.content = ''
        if msg.attachment:
            msg.attachment.delete(save=False)
        msg.attachment = None
        msg.attachment_name = ''
        msg.save()
        return Response({'message': 'Deleted for everyone', 'mode': 'everyone', 'id': msg.id})

    # mode == 'me' (default): hide only from the requesting user.
    msg.deleted_for.add(request.user)
    return Response({'message': 'Deleted for you', 'mode': 'me', 'id': msg.id})


# ── SAVE PUSH SUBSCRIPTION ─────────────────────────────────────────────
@api_view(['POST'])
def save_push_subscription_view(request):
    endpoint = request.data.get('endpoint')
    keys = request.data.get('keys', {})
    p256dh = keys.get('p256dh')
    auth = keys.get('auth')

    if not endpoint or not p256dh or not auth:
        return Response({'error': 'Invalid subscription data'}, status=400)

    PushSubscription.objects.update_or_create(
        endpoint=endpoint,
        defaults={'user': request.user, 'p256dh': p256dh, 'auth': auth}
    )
    return Response({'message': 'Subscribed'}, status=201)


def send_push_to_user(user, title, body, url='/'):
    """
    Sends a Web Push notification to every device the user has subscribed on.
    Called internally when a new chat message is created.
    """
    subscriptions = PushSubscription.objects.filter(user=user)
    for sub in subscriptions:
        try:
            webpush(
                subscription_info={
                    "endpoint": sub.endpoint,
                    "keys": {"p256dh": sub.p256dh, "auth": sub.auth}
                },
                data=json.dumps({"title": title, "body": body, "url": url}),
                vapid_private_key=settings.VAPID_PRIVATE_KEY_PATH,
                vapid_claims=settings.VAPID_CLAIMS.copy()
            )
        except WebPushException as e:
            # Subscription expired/invalid — clean it up
            if e.response is not None and e.response.status_code in (404, 410):
                sub.delete()
            else:
                print(f'Push error: {e}')


@api_view(['POST'])
@permission_classes([AllowAny])
def signup_create_company_view(request):
    email = request.data.get('email')
    password = request.data.get('password')
    full_name = request.data.get('full_name', '')
    company_name = request.data.get('company_name', '').strip()

    if not company_name:
        return Response({'error': 'Company name is required.'}, status=400)
    if User.objects.filter(email=email).exists():
        return Response({'error': 'Email already exists'}, status=400)

    password_error = validate_password_strength(password)
    if password_error:
        return Response({'error': password_error}, status=400)

    names = full_name.split(' ', 1)
    first_name = names[0] if names else ''
    last_name = names[1] if len(names) > 1 else ''

    try:
        with transaction.atomic():
            company = Company.objects.create(name=company_name)
            user = User.objects.create_user(
                username=email, email=email, password=password,
                first_name=first_name, last_name=last_name
            )
            emp_id = generate_employee_id(company)
            EmployeeProfile.objects.create(
                user=user, company=company, employee_id=emp_id,
                department='Admin', designation='Owner',
                is_admin=True, is_owner=True,
            )
    except Exception as e:
        print(f'Company signup error: {e}')
        return Response({'error': 'Signup failed'}, status=500)

    token, _ = Token.objects.get_or_create(user=user)
    serializer = UserSerializer(user, context={'request': request})
    return Response({
        'token': token.key,
        'user': serializer.data,
        'is_admin': True,
        'company_name': company.name,
    })


@api_view(['POST'])
def invite_admin_view(request):
    profile, err = get_admin_profile_or_403(request)
    if err:
        return err

    full_name = request.data.get('full_name', '').strip()
    email = request.data.get('email', '').strip().lower()
    password = request.data.get('password', '')

    if not full_name or not email or not password:
        return Response({'error': 'Full name, email, and password are required.'}, status=400)

    if User.objects.filter(email=email).exists():
        return Response({'error': 'An account with this email already exists.'}, status=400)

    password_error = validate_password_strength(password)
    if password_error:
        return Response({'error': password_error}, status=400)

    names = full_name.split(' ', 1)
    first_name = names[0] if names else ''
    last_name = names[1] if len(names) > 1 else ''

    try:
        with transaction.atomic():
            user = User.objects.create_user(
                username=email, email=email, password=password,
                first_name=first_name, last_name=last_name
            )
            emp_id = generate_employee_id(profile.company)
            EmployeeProfile.objects.create(
                user=user, company=profile.company, employee_id=emp_id,
                department='Admin', designation='Administrator', is_admin=True,
            )
            # No pending invite-link flow anymore — the account already
            # exists. We still write an AdminInvite row, marked as
            # immediately accepted, purely so this action shows up in
            # the superadmin's Admin Invites audit list.
            AdminInvite.objects.filter(company=profile.company, email=email, accepted=False).delete()
            AdminInvite.objects.create(
                company=profile.company, email=email, invited_by=request.user,
                accepted=True, accepted_at=timezone.now(),
            )
    except Exception as e:
        print(f'Co-admin creation error: {e}')
        return Response({'error': 'Failed to create co-admin account.'}, status=500)

    try:
        send_mail(
            subject=f'You have been added as an Admin on WorkTrack — {profile.company.name}',
            message=f'''Hello {full_name},

{request.user.get_full_name() or request.user.email} has added you as an Admin
for "{profile.company.name}" on WorkTrack.

Here are your login credentials:

Email: {email}
Password: {password}

Login here: {settings.FRONTEND_URL}

Please change your password after first login.

Regards,
WorkTrack Team''',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
        print(f'[OK] Co-admin credentials email sent to {email}')
    except Exception as e:
        print(f'[ERROR] Co-admin welcome email error: {e}')

    return Response({'message': f'Co-admin account created for {email}. Login credentials sent by email.'})


@api_view(['GET'])
@permission_classes([AllowAny])
def verify_invite_view(request, token):
    try:
        invite = AdminInvite.objects.get(token=token)
    except AdminInvite.DoesNotExist:
        return Response({'error': 'Invalid invite link.'}, status=404)

    if not invite.is_valid():
        return Response({'error': 'This invite has expired or was already used.'}, status=400)

    return Response({
        'valid': True,
        'email': invite.email,
        'company_name': invite.company.name,
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def accept_invite_view(request):
    token = request.data.get('token')
    password = request.data.get('password')
    full_name = request.data.get('full_name', '')

    try:
        invite = AdminInvite.objects.get(token=token)
    except AdminInvite.DoesNotExist:
        return Response({'error': 'Invalid invite link.'}, status=404)

    if not invite.is_valid():
        return Response({'error': 'This invite has expired or was already used.'}, status=400)

    if User.objects.filter(email=invite.email).exists():
        return Response({'error': 'An account with this email already exists.'}, status=400)

    password_error = validate_password_strength(password)
    if password_error:
        return Response({'error': password_error}, status=400)

    names = full_name.split(' ', 1)
    first_name = names[0] if names else ''
    last_name = names[1] if len(names) > 1 else ''

    try:
        with transaction.atomic():
            user = User.objects.create_user(
                username=invite.email, email=invite.email, password=password,
                first_name=first_name, last_name=last_name
            )
            emp_id = generate_employee_id(invite.company)
            EmployeeProfile.objects.create(
                user=user, company=invite.company, employee_id=emp_id,
                department='Admin', designation='Administrator', is_admin=True,
            )
            invite.accepted = True
            invite.accepted_at = timezone.now()
            invite.save()
    except Exception as e:
        print(f'Accept invite error: {e}')
        return Response({'error': 'Could not complete signup.'}, status=500)

    token_obj, _ = Token.objects.get_or_create(user=user)
    serializer = UserSerializer(user, context={'request': request})
    return Response({
        'token': token_obj.key,
        'user': serializer.data,
        'is_admin': True,
        'company_name': invite.company.name,
    })
# ══════════════════════════════════════════════════════════════════════
# SUPERADMIN — full cross-company database control panel
# ══════════════════════════════════════════════════════════════════════

def _require_superuser(request):
    if not (request.user and request.user.is_authenticated and request.user.is_superuser):
        return Response({'error': 'Superadmin access required'}, status=403)
    return None


def _serialize_employee_profile(e):
    return {
        'id': e.id,
        'user_id': e.user.id,
        'full_name': e.user.get_full_name() or e.user.email,
        'first_name': e.user.first_name,
        'last_name': e.user.last_name,
        'email': e.user.email,
        'company_id': e.company_id,
        'company_name': e.company.name if e.company else '—',
        'employee_id': e.employee_id,
        'department': e.department,
        'designation': e.designation,
        'phone': e.phone,
        'joining_date': str(e.joining_date) if e.joining_date else None,
        'is_admin': e.is_admin,
        'is_owner': e.is_owner,
    }


def _serialize_entry_with_company(e):
    d = _serialize_entry(e, include_employee_name=True)
    try:
        d['company_name'] = e.employee.employeeprofile.company.name if e.employee.employeeprofile.company else '—'
        d['company_id'] = e.employee.employeeprofile.company_id
    except Exception:
        d['company_name'] = '—'
        d['company_id'] = None
    return d


def _serialize_task_with_company(t):
    d = _serialize_task(t)
    try:
        d['company_name'] = t.assigned_to.employeeprofile.company.name if t.assigned_to.employeeprofile.company else '—'
        d['company_id'] = t.assigned_to.employeeprofile.company_id
    except Exception:
        d['company_name'] = '—'
        d['company_id'] = None
    return d


@api_view(['GET'])
def superadmin_dashboard_stats_view(request):
    err = _require_superuser(request)
    if err:
        return err
    return Response({
        'companies': Company.objects.count(),
        'employees': EmployeeProfile.objects.filter(is_admin=False).count(),
        'admins': EmployeeProfile.objects.filter(is_admin=True).count(),
        'work_entries': WorkEntry.objects.count(),
        'tasks': AssignedTask.objects.count(),
        'invites_pending': AdminInvite.objects.filter(accepted=False).count(),
        'invites_total': AdminInvite.objects.count(),
        'daily_reports': DailyReport.objects.count(),
    })


@api_view(['GET'])
def superadmin_filter_options_view(request):
    err = _require_superuser(request)
    if err:
        return err
    companies = list(Company.objects.values('id', 'name').order_by('name'))
    departments = list(
        EmployeeProfile.objects.exclude(department='').values_list('department', flat=True).distinct()
    )
    return Response({'companies': companies, 'departments': sorted(departments)})


@api_view(['GET'])
def superadmin_companies_view(request):
    err = _require_superuser(request)
    if err:
        return err

    is_active = request.query_params.get('is_active')
    search = request.query_params.get('search', '').strip()

    companies = Company.objects.all().order_by('-created_at')
    if is_active in ('true', 'false'):
        companies = companies.filter(is_active=(is_active == 'true'))
    if search:
        companies = companies.filter(name__icontains=search)

    data = []
    for c in companies:
        employees = EmployeeProfile.objects.filter(company=c)
        owner = employees.filter(is_owner=True).select_related('user').first()
        data.append({
            'id': c.id,
            'name': c.name,
            'is_active': c.is_active,
            'created_at': c.created_at.isoformat(),
            'owner_name': owner.user.get_full_name() if owner else '—',
            'owner_email': owner.user.email if owner else '',
            'employee_count': employees.filter(is_admin=False).count(),
            'admin_count': employees.filter(is_admin=True).count(),
            'total_people': employees.count(),
            'work_entry_count': WorkEntry.objects.filter(employee__employeeprofile__company=c).count(),
            'task_count': AssignedTask.objects.filter(assigned_to__employeeprofile__company=c).count(),
            'pending_invite_count': AdminInvite.objects.filter(company=c, accepted=False).count(),
        })
    return Response(data)


@api_view(['POST'])
def superadmin_create_company_view(request):
    err = _require_superuser(request)
    if err:
        return err

    name = request.data.get('name', '').strip()
    if not name:
        return Response({'error': 'Company name is required.'}, status=400)

    company = Company.objects.create(name=name)
    return Response({'id': company.id, 'name': company.name}, status=201)


@api_view(['GET', 'PUT', 'DELETE'])
def superadmin_company_detail_view(request, company_id):
    err = _require_superuser(request)
    if err:
        return err

    try:
        company = Company.objects.get(id=company_id)
    except Company.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)

    if request.method == 'GET':
        employees = EmployeeProfile.objects.filter(company=company).select_related('user')
        employees_data = [_serialize_employee_profile(e) for e in employees]

        work_entries = WorkEntry.objects.filter(
            employee__employeeprofile__company=company
        ).select_related('employee').order_by('-date')[:200]
        we_data = [_serialize_entry(w, include_employee_name=True) for w in work_entries]

        tasks = AssignedTask.objects.filter(
            assigned_to__employeeprofile__company=company
        ).select_related('assigned_to', 'assigned_by').order_by('-created_at')[:200]
        task_data = [_serialize_task(t) for t in tasks]

        invites = AdminInvite.objects.filter(company=company).select_related('invited_by').order_by('-created_at')
        invite_data = [{
            'id': i.id,
            'email': i.email,
            'accepted': i.accepted,
            'invited_by': i.invited_by.get_full_name() or i.invited_by.email,
            'created_at': i.created_at.isoformat(),
            'expires_at': i.expires_at.isoformat(),
        } for i in invites]

        daily_reports = DailyReport.objects.filter(
            employee__employeeprofile__company=company
        ).order_by('-date')[:100]
        dr_data = DailyReportSerializer(daily_reports, many=True).data

        return Response({
            'id': company.id,
            'name': company.name,
            'is_active': company.is_active,
            'created_at': company.created_at.isoformat(),
            'employees': employees_data,
            'work_entries': we_data,
            'assigned_tasks': task_data,
            'admin_invites': invite_data,
            'daily_reports': dr_data,
        })

    elif request.method == 'PUT':
        company.name = request.data.get('name', company.name)
        if 'is_active' in request.data:
            company.is_active = request.data.get('is_active')
        company.save()
        return Response({'id': company.id, 'name': company.name, 'is_active': company.is_active})

    elif request.method == 'DELETE':
        company.delete()
        return Response({'message': 'Company and all its data deleted'})


# ── GLOBAL cross-company employee list (matches Django's "Employee profiles" screen) ──
@api_view(['GET'])
def superadmin_all_employees_view(request):
    err = _require_superuser(request)
    if err:
        return err

    qs = EmployeeProfile.objects.select_related('user', 'company').all()

    company_id = request.query_params.get('company')
    is_admin = request.query_params.get('is_admin')
    is_owner = request.query_params.get('is_owner')
    department = request.query_params.get('department')
    search = request.query_params.get('search', '').strip()

    if company_id:
        qs = qs.filter(company_id=company_id)
    if is_admin in ('true', 'false'):
        qs = qs.filter(is_admin=(is_admin == 'true'))
    if is_owner in ('true', 'false'):
        qs = qs.filter(is_owner=(is_owner == 'true'))
    if department:
        qs = qs.filter(department=department)
    if search:
        qs = (
            qs.filter(user__email__icontains=search) |
            qs.filter(user__first_name__icontains=search) |
            qs.filter(user__last_name__icontains=search) |
            qs.filter(employee_id__icontains=search)
        )

    qs = qs.order_by('company__name', 'employee_id').distinct()
    return Response([_serialize_employee_profile(e) for e in qs])


@api_view(['GET', 'PUT', 'DELETE'])
def superadmin_employee_detail_view(request, profile_id):
    err = _require_superuser(request)
    if err:
        return err

    try:
        profile = EmployeeProfile.objects.select_related('user', 'company').get(id=profile_id)
    except EmployeeProfile.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)

    if request.method == 'GET':
        return Response(_serialize_employee_profile(profile))

    elif request.method == 'PUT':
        profile.department = request.data.get('department', profile.department)
        profile.designation = request.data.get('designation', profile.designation)
        profile.phone = request.data.get('phone', profile.phone)
        profile.employee_id = request.data.get('employee_id', profile.employee_id)

        if 'joining_date' in request.data:
            profile.joining_date = request.data.get('joining_date') or None
        if 'is_admin' in request.data:
            profile.is_admin = request.data.get('is_admin')
        if 'is_owner' in request.data:
            profile.is_owner = request.data.get('is_owner')
        if 'company_id' in request.data and request.data.get('company_id'):
            try:
                profile.company = Company.objects.get(id=request.data.get('company_id'))
            except Company.DoesNotExist:
                pass

        profile.save()
        return Response(_serialize_employee_profile(profile))

    elif request.method == 'DELETE':
        profile.user.delete()  # cascades and removes the EmployeeProfile too
        return Response({'message': 'Employee removed'})


# ── GLOBAL cross-company work entries list ──
@api_view(['GET'])
def superadmin_all_work_entries_view(request):
    err = _require_superuser(request)
    if err:
        return err

    qs = WorkEntry.objects.select_related('employee').all()

    company_id = request.query_params.get('company')
    status_f = request.query_params.get('status')
    search = request.query_params.get('search', '').strip()

    if company_id:
        qs = qs.filter(employee__employeeprofile__company_id=company_id)
    if status_f:
        qs = qs.filter(status=status_f)
    if search:
        qs = (
            qs.filter(project_name__icontains=search) |
            qs.filter(employee__first_name__icontains=search) |
            qs.filter(employee__last_name__icontains=search)
        )

    qs = qs.order_by('-date', '-submitted_at')[:300]
    return Response([_serialize_entry_with_company(e) for e in qs])


@api_view(['GET', 'PUT', 'DELETE'])
def superadmin_work_entry_detail_view(request, entry_id):
    err = _require_superuser(request)
    if err:
        return err
    try:
        entry = WorkEntry.objects.select_related('employee').get(id=entry_id)
    except WorkEntry.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)

    if request.method == 'GET':
        return Response(_serialize_entry_with_company(entry))

    elif request.method == 'PUT':
        for field in ('project_name', 'task_done', 'date', 'remark', 'status',
                      'review_status', 'admin_comment'):
            if field in request.data:
                setattr(entry, field, request.data.get(field))
        for field in ('planned_minutes', 'actual_minutes'):
            if field in request.data:
                val = request.data.get(field)
                setattr(entry, field, int(val) if val not in (None, '') else None)
        entry.save()
        return Response(_serialize_entry_with_company(entry))

    elif request.method == 'DELETE':
        entry.delete()
        return Response({'message': 'Work entry deleted'})


# ── GLOBAL cross-company assigned tasks list ──
@api_view(['GET'])
def superadmin_all_tasks_view(request):
    err = _require_superuser(request)
    if err:
        return err

    qs = AssignedTask.objects.select_related('assigned_to', 'assigned_by').all()

    company_id = request.query_params.get('company')
    status_f = request.query_params.get('status')
    search = request.query_params.get('search', '').strip()

    if company_id:
        qs = qs.filter(assigned_to__employeeprofile__company_id=company_id)
    if status_f:
        qs = qs.filter(status=status_f)
    if search:
        qs = qs.filter(project_name__icontains=search)

    qs = qs.order_by('-created_at')[:300]
    return Response([_serialize_task_with_company(t) for t in qs])


@api_view(['GET', 'PUT', 'DELETE'])
def superadmin_task_detail_view(request, task_id):
    err = _require_superuser(request)
    if err:
        return err
    try:
        task = AssignedTask.objects.select_related('assigned_to', 'assigned_by').get(id=task_id)
    except AssignedTask.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)

    if request.method == 'GET':
        return Response(_serialize_task_with_company(task))

    elif request.method == 'PUT':
        for field in ('project_name', 'task_description', 'deadline', 'status'):
            if field in request.data:
                val = request.data.get(field)
                setattr(task, field, val or None if field == 'deadline' else val)
        for field in ('planned_minutes', 'actual_minutes'):
            if field in request.data:
                val = request.data.get(field)
                setattr(task, field, int(val) if val not in (None, '') else None)
        task.save()
        return Response(_serialize_task_with_company(task))

    elif request.method == 'DELETE':
        task.delete()
        return Response({'message': 'Task deleted'})


# ── GLOBAL cross-company admin invites list ──
@api_view(['GET'])
def superadmin_all_invites_view(request):
    err = _require_superuser(request)
    if err:
        return err

    qs = AdminInvite.objects.select_related('company', 'invited_by').all()

    company_id = request.query_params.get('company')
    accepted = request.query_params.get('accepted')

    if company_id:
        qs = qs.filter(company_id=company_id)
    if accepted in ('true', 'false'):
        qs = qs.filter(accepted=(accepted == 'true'))

    qs = qs.order_by('-created_at')
    data = [{
        'id': i.id,
        'email': i.email,
        'company_id': i.company_id,
        'company_name': i.company.name,
        'accepted': i.accepted,
        'invited_by': i.invited_by.get_full_name() or i.invited_by.email,
        'created_at': i.created_at.isoformat(),
        'expires_at': i.expires_at.isoformat(),
    } for i in qs]
    return Response(data)


def _serialize_invite(i):
    return {
        'id': i.id,
        'email': i.email,
        'company_id': i.company_id,
        'company_name': i.company.name,
        'accepted': i.accepted,
        'invited_by': i.invited_by.get_full_name() or i.invited_by.email,
        'created_at': i.created_at.isoformat(),
        'expires_at': i.expires_at.isoformat(),
    }


@api_view(['GET', 'PUT', 'DELETE'])
def superadmin_invite_detail_view(request, invite_id):
    err = _require_superuser(request)
    if err:
        return err
    try:
        invite = AdminInvite.objects.select_related('company', 'invited_by').get(id=invite_id)
    except AdminInvite.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)

    if request.method == 'GET':
        return Response(_serialize_invite(invite))

    elif request.method == 'PUT':
        if 'accepted' in request.data:
            invite.accepted = bool(request.data.get('accepted'))
            if invite.accepted:
                invite.accepted_at = invite.accepted_at or timezone.now()
            else:
                invite.accepted_at = None
        if request.data.get('resend'):
            invite.expires_at = timezone.now() + timedelta(hours=48)
            invite.accepted = False
            invite.accepted_at = None
        invite.save()
        return Response(_serialize_invite(invite))

    elif request.method == 'DELETE':
        invite.delete()
        return Response({'message': 'Invite deleted'})


# ── GLOBAL cross-company daily reports list ──
@api_view(['GET'])
def superadmin_all_reports_view(request):
    err = _require_superuser(request)
    if err:
        return err

    qs = DailyReport.objects.select_related('employee').all()

    company_id = request.query_params.get('company')
    status_f = request.query_params.get('status')
    search = request.query_params.get('search', '').strip()

    if company_id:
        qs = qs.filter(employee__employeeprofile__company_id=company_id)
    if status_f:
        qs = qs.filter(status=status_f)
    if search:
        qs = (
            qs.filter(title__icontains=search) |
            qs.filter(employee__first_name__icontains=search) |
            qs.filter(employee__last_name__icontains=search)
        )

    qs = qs.order_by('-date')[:300]
    data = []
    for r in qs:
        d = DailyReportSerializer(r).data
        try:
            d['company_name'] = r.employee.employeeprofile.company.name if r.employee.employeeprofile.company else '—'
            d['company_id'] = r.employee.employeeprofile.company_id
        except Exception:
            d['company_name'] = '—'
            d['company_id'] = None
        data.append(d)
    return Response(data)


@api_view(['GET', 'PUT', 'DELETE'])
def superadmin_report_detail_view(request, report_id):
    err = _require_superuser(request)
    if err:
        return err
    try:
        report = DailyReport.objects.select_related('employee').get(id=report_id)
    except DailyReport.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)

    if request.method == 'GET':
        d = DailyReportSerializer(report).data
        try:
            d['company_name'] = report.employee.employeeprofile.company.name if report.employee.employeeprofile.company else '—'
        except Exception:
            d['company_name'] = '—'
        return Response(d)

    elif request.method == 'PUT':
        for field in ('title', 'date', 'challenges', 'plan_for_tomorrow',
                      'status', 'manager_comment'):
            if field in request.data:
                setattr(report, field, request.data.get(field))
        if 'hours_worked' in request.data:
            report.hours_worked = float(request.data.get('hours_worked') or 0)
        report.save()
        return Response(DailyReportSerializer(report).data)

    elif request.method == 'DELETE':
        report.delete()
        return Response({'message': 'Report deleted'})


# ── GLOBAL cross-company users (raw auth accounts) ──
def _serialize_user_full(u):
    try:
        profile = u.employeeprofile
        company_name = profile.company.name if profile.company else '—'
        company_id = profile.company_id
        is_admin_flag = profile.is_admin
        employee_id = profile.employee_id
    except EmployeeProfile.DoesNotExist:
        company_name = '—'
        company_id = None
        is_admin_flag = False
        employee_id = ''
    return {
        'id': u.id,
        'username': u.username,
        'email': u.email,
        'first_name': u.first_name,
        'last_name': u.last_name,
        'full_name': u.get_full_name() or u.username,
        'is_active': u.is_active,
        'is_staff': u.is_staff,
        'is_superuser': u.is_superuser,
        'date_joined': u.date_joined.isoformat(),
        'last_login': u.last_login.isoformat() if u.last_login else None,
        'company_name': company_name,
        'company_id': company_id,
        'is_admin': is_admin_flag,
        'employee_id': employee_id,
    }


@api_view(['GET'])
def superadmin_all_users_view(request):
    err = _require_superuser(request)
    if err:
        return err

    search = request.query_params.get('search', '').strip()
    qs = User.objects.all().order_by('-date_joined')
    if search:
        qs = (
            qs.filter(email__icontains=search) |
            qs.filter(username__icontains=search) |
            qs.filter(first_name__icontains=search) |
            qs.filter(last_name__icontains=search)
        ).distinct()
    return Response([_serialize_user_full(u) for u in qs])


@api_view(['POST'])
def superadmin_create_user_view(request):
    err = _require_superuser(request)
    if err:
        return err

    email = request.data.get('email', '').strip()
    password = request.data.get('password', '')
    if not email or not password:
        return Response({'error': 'Email and password are required.'}, status=400)
    if User.objects.filter(email=email).exists():
        return Response({'error': 'A user with this email already exists.'}, status=400)

    pw_error = validate_password_strength(password)
    if pw_error:
        return Response({'error': pw_error}, status=400)

    is_super = bool(request.data.get('is_superuser', False))
    user = User.objects.create_user(
        username=email, email=email, password=password,
        first_name=request.data.get('first_name', ''),
        last_name=request.data.get('last_name', ''),
        is_superuser=is_super,
        is_staff=is_super,
    )
    return Response(_serialize_user_full(user), status=201)


@api_view(['GET', 'PUT', 'DELETE'])
def superadmin_user_detail_view(request, user_id):
    err = _require_superuser(request)
    if err:
        return err
    try:
        u = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)

    if request.method == 'GET':
        return Response(_serialize_user_full(u))

    elif request.method == 'PUT':
        u.first_name = request.data.get('first_name', u.first_name)
        u.last_name = request.data.get('last_name', u.last_name)
        u.email = request.data.get('email', u.email)
        if 'is_active' in request.data:
            u.is_active = bool(request.data.get('is_active'))
        if 'is_superuser' in request.data:
            u.is_superuser = bool(request.data.get('is_superuser'))
            if u.is_superuser:
                u.is_staff = True
        new_password = request.data.get('new_password')
        if new_password:
            pw_error = validate_password_strength(new_password)
            if pw_error:
                return Response({'error': pw_error}, status=400)
            u.set_password(new_password)
        u.save()
        return Response(_serialize_user_full(u))

    elif request.method == 'DELETE':
        if u.id == request.user.id:
            return Response({'error': "You cannot delete your own account."}, status=400)
        u.delete()
        return Response({'message': 'User deleted'})


# ══════════════════════════════════════════════════════════════════════
# ATTENDANCE — GPS check-in / check-out
# ══════════════════════════════════════════════════════════════════════

def _haversine_meters(lat1, lon1, lat2, lon2):
    """Straight-line distance between two lat/lng points, in meters."""
    R = 6371000  # Earth radius, meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def _serialize_attendance(a):
    try:
        office_address = a.employee.employeeprofile.company.office_address
    except Exception:
        office_address = ''
    return {
        'id': a.id,
        'date': str(a.date),
        'employee_id': a.employee.id,
        'employee_name': a.employee.get_full_name(),
        'check_in_time': a.check_in_time.isoformat() if a.check_in_time else None,
        'check_in_latitude': a.check_in_latitude,
        'check_in_longitude': a.check_in_longitude,
        'check_in_address': a.check_in_address,
        'check_in_distance_meters': a.check_in_distance_meters,
        'check_out_time': a.check_out_time.isoformat() if a.check_out_time else None,
        'check_out_latitude': a.check_out_latitude,
        'check_out_longitude': a.check_out_longitude,
        'check_out_address': a.check_out_address,
        'check_out_distance_meters': a.check_out_distance_meters,
        'office_address': office_address,
    }


@api_view(['GET', 'PUT'])
def office_location_view(request):
    """
    GET: any authenticated company member can read the office location
    and geofence radius — the attendance page needs this to draw the
    map and show "how far am I from the office" before checking in.
    PUT: admin-only, sets/updates it.
    """
    try:
        profile = request.user.employeeprofile
    except EmployeeProfile.DoesNotExist:
        return Response({'error': 'Profile not found'}, status=404)

    company = profile.company
    if not company:
        return Response({'error': 'No company on this account'}, status=404)

    if request.method == 'GET':
        return Response({
            'latitude': company.office_latitude,
            'longitude': company.office_longitude,
            'radius_meters': company.office_radius_meters,
            'address': company.office_address,
        })

    if not profile.is_admin:
        return Response({'error': 'Only admins can set the office location'}, status=403)

    lat = request.data.get('latitude')
    lng = request.data.get('longitude')
    radius = request.data.get('radius_meters')
    address = request.data.get('address')

    try:
        if lat is not None:
            company.office_latitude = float(lat)
        if lng is not None:
            company.office_longitude = float(lng)
        if radius is not None:
            company.office_radius_meters = int(radius)
        if address is not None:
            company.office_address = str(address)[:300]
    except (TypeError, ValueError):
        return Response({'error': 'Invalid latitude, longitude, or radius'}, status=400)

    company.save()
    return Response({
        'latitude': company.office_latitude,
        'longitude': company.office_longitude,
        'radius_meters': company.office_radius_meters,
        'address': company.office_address,
    })


@api_view(['POST'])
def attendance_check_in_view(request):
    lat = request.data.get('latitude')
    lng = request.data.get('longitude')
    address = request.data.get('address', '') or ''

    if lat is None or lng is None:
        return Response({'error': 'latitude and longitude are required'}, status=400)

    try:
        lat = float(lat)
        lng = float(lng)
    except (TypeError, ValueError):
        return Response({'error': 'latitude and longitude must be numbers'}, status=400)

    try:
        profile = request.user.employeeprofile
    except EmployeeProfile.DoesNotExist:
        return Response({'error': 'Profile not found'}, status=404)

    today = timezone.now().date()
    record, _ = Attendance.objects.get_or_create(employee=request.user, date=today)

    if record.check_in_time:
        return Response({'error': 'Already checked in today'}, status=400)

    distance = None
    company = profile.company
    if company and company.office_latitude is not None and company.office_longitude is not None:
        distance = _haversine_meters(lat, lng, company.office_latitude, company.office_longitude)

    record.check_in_time = timezone.now()
    record.check_in_latitude = lat
    record.check_in_longitude = lng
    record.check_in_address = address[:500]
    record.check_in_distance_meters = distance
    record.save()

    return Response(_serialize_attendance(record), status=201)


@api_view(['POST'])
def attendance_check_out_view(request):
    lat = request.data.get('latitude')
    lng = request.data.get('longitude')
    address = request.data.get('address', '') or ''

    if lat is None or lng is None:
        return Response({'error': 'latitude and longitude are required'}, status=400)

    try:
        lat = float(lat)
        lng = float(lng)
    except (TypeError, ValueError):
        return Response({'error': 'latitude and longitude must be numbers'}, status=400)

    try:
        profile = request.user.employeeprofile
    except EmployeeProfile.DoesNotExist:
        return Response({'error': 'Profile not found'}, status=404)

    today = timezone.now().date()
    try:
        record = Attendance.objects.get(employee=request.user, date=today)
    except Attendance.DoesNotExist:
        return Response({'error': 'You have not checked in today'}, status=400)

    if not record.check_in_time:
        return Response({'error': 'You have not checked in today'}, status=400)
    if record.check_out_time:
        return Response({'error': 'Already checked out today'}, status=400)

    distance = None
    company = profile.company
    if company and company.office_latitude is not None and company.office_longitude is not None:
        distance = _haversine_meters(lat, lng, company.office_latitude, company.office_longitude)

    record.check_out_time = timezone.now()
    record.check_out_latitude = lat
    record.check_out_longitude = lng
    record.check_out_address = address[:500]
    record.check_out_distance_meters = distance
    record.save()

    return Response(_serialize_attendance(record))


@api_view(['GET'])
def my_attendance_view(request):
    """Employee's own attendance history, optionally filtered by month/year."""
    month = request.query_params.get('month')
    year = request.query_params.get('year')
    qs = Attendance.objects.filter(employee=request.user)
    if month and year:
        qs = qs.filter(date__month=month, date__year=year)
    qs = qs.order_by('-date')
    return Response([_serialize_attendance(a) for a in qs])


@api_view(['GET'])
def admin_employee_attendance_view(request, employee_id):
    """Admin viewing one employee's attendance (company-scoped)."""
    profile, err = get_admin_profile_or_403(request)
    if err:
        return err

    try:
        employee = User.objects.get(id=employee_id, employeeprofile__company=profile.company)
    except User.DoesNotExist:
        return Response({'error': 'Employee not found'}, status=404)

    month = request.query_params.get('month')
    year = request.query_params.get('year')
    qs = Attendance.objects.filter(employee=employee)
    if month and year:
        qs = qs.filter(date__month=month, date__year=year)
    qs = qs.order_by('-date')
    return Response([_serialize_attendance(a) for a in qs])


@api_view(['GET'])
def admin_attendance_today_view(request):
    """
    Admin dashboard summary: every employee in the company, with
    today's attendance record if one exists (or None if they haven't
    checked in yet). Used to power an "who's in today" overview.
    """
    profile, err = get_admin_profile_or_403(request)
    if err:
        return err

    today = timezone.now().date()
    employees = User.objects.filter(
        employeeprofile__company=profile.company,
        employeeprofile__is_admin=False,
    ).select_related('employeeprofile')

    today_records = {
        a.employee_id: a
        for a in Attendance.objects.filter(employee__in=employees, date=today)
    }

    data = []
    for emp in employees:
        record = today_records.get(emp.id)
        data.append({
            'employee_id': emp.id,
            'employee_name': emp.get_full_name() or emp.email,
            'department': emp.employeeprofile.department if hasattr(emp, 'employeeprofile') else '',
            'attendance': _serialize_attendance(record) if record else None,
        })
    return Response(data)


# ========================================
# TEMPLATE VIEWS - Frontend pages
# ========================================

from django.shortcuts import render


def page_admin_worklog_view(request):
    """Admin work log page"""
    return render(request, 'admin/worklog.html', {'active': 'worklog', 'role': 'admin'})


def page_admin_profile_view(request):
    """Admin profile page"""
    return render(request, 'admin/profile.html', {'active': 'profile', 'role': 'admin'})


def page_admin_all_reports_view(request):
    """Admin all reports page"""
    return render(request, 'admin/all-reports.html', {'active': 'all-reports', 'role': 'admin'})


def page_admin_employees_view(request):
    """Admin employees page"""
    return render(request, 'admin/employees.html', {'active': 'employees', 'role': 'admin'})


def page_admin_analytics_view(request):
    """Admin analytics page"""
    return render(request, 'admin/analytics.html', {'active': 'analytics', 'role': 'admin'})


def page_admin_chat_view(request):
    """Admin chat page"""
    return render(request, 'admin/chat.html', {'active': 'chat', 'role': 'admin'})


def employee_worklog_view(request):
    """Employee work log page"""
    return render(request, 'employee/worklog.html', {'active': 'worklog', 'role': 'employee'})


def employee_submit_report_view(request):
    """Employee submit report page"""
    return render(request, 'employee/submit-report.html', {'active': 'submit-report', 'role': 'employee'})


def employee_my_reports_view(request):
    """Employee my reports page"""
    return render(request, 'employee/my-reports.html', {'active': 'my-reports', 'role': 'employee'})


def employee_profile_view(request):
    """Employee profile page"""
    return render(request, 'employee/profile.html', {'active': 'profile', 'role': 'employee'})


def employee_chat_view(request):
    """Employee chat page"""
    return render(request, 'employee/chat.html', {'active': 'chat', 'role': 'employee'})


def employee_chart_view(request):
    """Employee analytics/chart page"""
    return render(request, 'employee/chart.html', {'active': 'chart', 'role': 'employee'})


def admin_test_view(request):
    """Test page for admin base template"""
    return render(request, 'admin/test.html', {'active': 'worklog', 'role': 'admin'})


def employee_test_view(request):
    """Test page for employee base template"""
    return render(request, 'employee/test.html', {'active': 'worklog', 'role': 'employee'})


def employee_attendance_view(request):
    """Employee GPS check-in/check-out page"""
    return render(request, 'employee/attendance.html', {'active': 'attendance', 'role': 'employee'})


def page_admin_attendance_view(request):
    """Admin attendance overview page"""
    return render(request, 'admin/attendance.html', {'active': 'attendance', 'role': 'admin'})