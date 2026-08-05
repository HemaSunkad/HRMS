from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import secrets
from django.utils import timezone
from datetime import timedelta

class Company(models.Model):
    name = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    # Office GPS location + geofence radius, used by the attendance
    # check-in/check-out feature to compute how far an employee was
    # from the office when they punched in. Left null until an admin
    # sets it on the Attendance page — attendance still works without
    # it, it just won't show a distance-from-office figure.
    office_latitude = models.FloatField(null=True, blank=True)
    office_longitude = models.FloatField(null=True, blank=True)
    office_radius_meters = models.IntegerField(default=200)
    office_address = models.CharField(max_length=300, blank=True)

    def __str__(self):
        return self.name
    class Meta:
        verbose_name_plural = 'Companies'   # ← ADD THIS

def generate_invite_token():
    return secrets.token_urlsafe(32)


class AdminInvite(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='invites')
    email = models.EmailField()
    token = models.CharField(max_length=64, unique=True, default=generate_invite_token)
    invited_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_invites')
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(blank=True)
    accepted = models.BooleanField(default=False)
    accepted_at = models.DateTimeField(null=True, blank=True)

    def is_valid(self):
        return not self.accepted and timezone.now() < self.expires_at

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=48)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.email} → {self.company.name}'

class EmployeeProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, related_name='employees')  # NEW
    is_owner = models.BooleanField(default=False)
    employee_id = models.CharField(max_length=20)
    department = models.CharField(max_length=100)
    designation = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, blank=True)
    joining_date = models.DateField(null=True, blank=True)
    is_admin = models.BooleanField(default=False)
    photo = models.ImageField(upload_to='profile_photos/', null=True, blank=True)
    # Updated by heartbeat_view every ~20s while a WorkTrack tab is open
    # and active; _is_online() compares this against ONLINE_THRESHOLD_SECONDS
    # to decide the green/gray dot shown in chat. Was referenced by
    # views.py (heartbeat_view, user_status_view, chat_rooms_view) before
    # this field existed on the model, which is why /api/heartbeat/ broke.
    last_active = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.employee_id}"
    class Meta:
        unique_together = ('company', 'employee_id')


class DailyReport(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    employee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reports')
    title = models.CharField(max_length=200)
    date = models.DateField()
    hours_worked = models.FloatField()
    tasks = models.JSONField(default=list)
    challenges = models.TextField(blank=True)
    plan_for_tomorrow = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    manager_comment = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.employee.get_full_name()} - {self.date}"

    class Meta:
        ordering = ['-date']
class WorkEntry(models.Model):
    STATUS_CHOICES = [
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('paused', 'Paused'),
        ('completed', 'Completed'),
        ('reassigned', 'Reassigned'),
    ]
    REVIEW_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    employee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='work_entries')
    date = models.DateField()
    project_name = models.CharField(max_length=200)
    task_done = models.TextField()
    planned_minutes = models.IntegerField(default=0)
    start_time = models.DateTimeField(null=True, blank=True)
    # original_start_time: timestamp of the VERY FIRST time this entry was
    # started, set once and never touched again by pause/resume. `start_time`
    # itself gets overwritten to "now" every time an entry is resumed (so the
    # backend can correctly measure that specific work session) — which means
    # displaying `start_time` directly in the UI silently shows the time of
    # the *last* resume instead of when the work truly began, producing
    # confusing mismatches against the Actual/Result columns after any pause
    # cycle. original_start_time is the stable value the UI should show.
    original_start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    actual_minutes = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='not_started')
    remark = models.TextField(blank=True)
    review_status = models.CharField(max_length=20, choices=REVIEW_CHOICES, default='pending')
    admin_comment = models.TextField(blank=True)
    admin_comment = models.TextField(blank=True)
    is_manual_entry = models.BooleanField(default=False)
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Pause tracking fields
    accumulated_minutes = models.IntegerField(default=0)
    pause_count = models.IntegerField(default=0)
    # paused_at: timestamp the *current* pause began (null while not paused) —
    # lets the frontend render a live, ticking "time paused so far" counter.
    paused_at = models.DateTimeField(null=True, blank=True)
    # total_paused_seconds: running total of ALL pause durations for this
    # entry, across every pause/resume cycle. Preserved through resume so a
    # second pause continues counting instead of restarting from zero, and
    # is shown in the Result column once the entry is completed.
    total_paused_seconds = models.IntegerField(default=0)

    # Reassignment fields
    original_owner = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='originally_owned_entries'
    )
    is_reassigned = models.BooleanField(default=False)
    reassigned_from = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='reassigned_out_entries'
    )
    reassigned_to = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='reassigned_in_entries'
    )
    reassigned_at = models.DateTimeField(null=True, blank=True)
    reassigned_by_admin = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='admin_reassigned_entries'
    )

    def __str__(self):
        return f"{self.employee.get_full_name()} - {self.date} - {self.project_name}"

    class Meta:
        ordering = ['-date', '-submitted_at']


class AssignedTask(models.Model):
    STATUS_CHOICES = [
        ('assigned', 'Assigned'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ]

    assigned_to = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assigned_tasks')
    assigned_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tasks_given')
    project_name = models.CharField(max_length=200)
    task_description = models.TextField()
    deadline = models.DateField(null=True, blank=True)
    planned_minutes = models.IntegerField(default=0)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    actual_minutes = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='assigned')
    created_at = models.DateTimeField(auto_now_add=True)

    # Reassignment fields
    original_owner = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='originally_assigned_tasks'
    )
    is_reassigned = models.BooleanField(default=False)
    reassigned_from = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='reassigned_out_tasks'
    )
    reassigned_to = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='reassigned_in_tasks'
    )
    reassigned_at = models.DateTimeField(null=True, blank=True)
    reassigned_by_admin = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='admin_reassigned_tasks'
    )

    def __str__(self):
        return f"{self.project_name} → {self.assigned_to.get_full_name()}"

    class Meta:
        ordering = ['-created_at']


class ReassignmentLog(models.Model):
    ITEM_TYPE_CHOICES = [
        ('work_entry', 'Work Entry'),
        ('assigned_task', 'Assigned Task'),
    ]

    item_type = models.CharField(max_length=20, choices=ITEM_TYPE_CHOICES)
    item_id = models.IntegerField()
    from_employee = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='reassignment_log_from'
    )
    to_employee = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='reassignment_log_to'
    )
    reassigned_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='reassignment_log_by'
    )
    reassigned_at = models.DateTimeField(auto_now_add=True)
    note = models.TextField(blank=True)

    def __str__(self):
        return f"{self.item_type} #{self.item_id}: {self.from_employee} → {self.to_employee}"

    class Meta:
        ordering = ['-reassigned_at']
class ChatRoom(models.Model):
    ROOM_TYPES = [('group', 'Group'), ('direct', 'Direct')]
    name = models.CharField(max_length=200, blank=True)
    room_type = models.CharField(max_length=10, choices=ROOM_TYPES, default='group')
    participants = models.ManyToManyField(User, related_name='chat_rooms', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_rooms')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True, related_name='chat_rooms')
    # True for the one auto-created, company-wide "Team Chat" group that
    # every non-admin employee is added to automatically. User-created
    # groups (via "New Group") are False, and are never auto-populated
    # with new hires the way the default group is.
    is_default_group = models.BooleanField(default=False)
    def __str__(self):
        return self.name or f'DM Room {self.id}'

class ChatMessage(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    content = models.TextField(blank=True)
    attachment = models.FileField(upload_to='chat_attachments/', null=True, blank=True)
    attachment_name = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    # "Delete for everyone" — set by the original sender; content and
    # attachment are cleared server-side and every viewer sees a placeholder.
    is_deleted_for_everyone = models.BooleanField(default=False)
    # "Delete for me" — per-viewer hide, doesn't affect other participants.
    deleted_for = models.ManyToManyField(User, related_name='deleted_messages', blank=True)
    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.sender.get_full_name()}: {self.content[:50]}'  
class ChatReadStatus(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='read_statuses')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_read_statuses')
    last_read_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('room', 'user')
class PushSubscription(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='push_subscriptions')
    endpoint = models.URLField(max_length=500, unique=True)
    p256dh = models.CharField(max_length=255)
    auth = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.endpoint[:50]}"


class Attendance(models.Model):
    """
    One row per employee per calendar day. Check-in captures GPS
    coordinates (from the browser's Geolocation API) plus a
    human-readable address (reverse-geocoded client-side via
    Nominatim/OpenStreetMap), and the straight-line distance in meters
    from the company's configured office location — computed here so
    it's an authoritative server-side value, not just trusted from the
    client. Check-out mirrors the same fields.
    """
    employee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='attendance_records')
    date = models.DateField()

    check_in_time = models.DateTimeField(null=True, blank=True)
    check_in_latitude = models.FloatField(null=True, blank=True)
    check_in_longitude = models.FloatField(null=True, blank=True)
    check_in_address = models.CharField(max_length=500, blank=True)
    check_in_distance_meters = models.FloatField(null=True, blank=True)

    check_out_time = models.DateTimeField(null=True, blank=True)
    check_out_latitude = models.FloatField(null=True, blank=True)
    check_out_longitude = models.FloatField(null=True, blank=True)
    check_out_address = models.CharField(max_length=500, blank=True)
    check_out_distance_meters = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f"{self.employee.get_full_name()} - {self.date}"

    class Meta:
        unique_together = ('employee', 'date')
        ordering = ['-date']