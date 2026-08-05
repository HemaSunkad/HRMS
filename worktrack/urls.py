from django.contrib import admin
from django.urls import path, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from reports import views
from reports import views as page_views

urlpatterns = [
    path('django-admin/', admin.site.urls),
    path('api/login/', views.login_view),
    path('api/register/', views.register_view),
    path('api/admin/google-login/', views.google_admin_login_view),
    path('api/logout/', views.logout_view),
    path('api/me/', views.me_view),
    path('api/profile/update/', views.update_profile_view),
    path('api/profile/change-password/', views.change_password_view),
    path('api/reports/', views.reports_view),
    path('api/reports/<int:pk>/', views.report_detail_view),
    path('api/employee/stats/', views.employee_stats_view),
    path('api/employee/analytics/', views.employee_analytics_view),
    path('api/employee/entries/', views.work_entries_view),
    path('api/employee/entries/<int:pk>/', views.work_entry_detail_view),
    path('api/employee/assigned-tasks/', views.employee_assigned_tasks_view),
    path('api/employee/assigned-tasks/<int:pk>/action/', views.assigned_task_action_view),
    path('api/admin/stats/', views.admin_stats_view),
    path('api/admin/reports/', views.admin_all_reports_view),
    path('api/admin/reports/<int:pk>/review/', views.admin_review_report_view),
    path('api/admin/employees/', views.admin_employees_view),
    path('api/admin/employees/<int:employee_id>/entries/', views.admin_employee_entries_view),
    path('api/admin/employees/<int:employee_id>/delete/', views.delete_employee_view),
    path('api/admin/entries/<int:pk>/review/', views.admin_review_entry_view),
    path('api/admin/entries/<int:pk>/pause/', views.admin_pause_entry_view),
    path('api/admin/assign-task/', views.assign_task_view),
    path('api/admin/analytics/', views.admin_analytics_view),
    path('api/verify-admin-code/', views.verify_admin_code_view),
    path('api/work-entries/<int:pk>/reassign/', views.reassign_work_entry_view),
    path('api/assigned-tasks/<int:pk>/reassign/', views.reassign_assigned_task_view),
    path('api/employees/all/', views.all_employees_for_reassign_view),

    # ── ONLINE STATUS (heartbeat) ───────────────────────────────────
    path('api/heartbeat/', views.heartbeat_view),
    path('api/users/<int:user_id>/status/', views.user_status_view),

    # ── CHAT ─────────────────────────────────────────────────────────
    path('api/chat/rooms/', views.chat_rooms_view),
    path('api/chat/rooms/dm/', views.create_dm_room_view),
    path('api/chat/rooms/group/', views.create_group_room_view),
    path('api/chat/rooms/<int:room_id>/messages/', views.chat_messages_view),
    path('api/chat/rooms/<int:room_id>/read-status/', views.chat_room_read_status_view),
    path('api/chat/rooms/<int:room_id>/read/', views.mark_room_read_view),
    path('api/chat/rooms/<int:room_id>/delete/', views.delete_chat_room_view),
    path('api/chat/users/', views.all_users_for_chat_view),
    path('api/chat/recent/', views.recent_messages_view),
    path('api/chat/unread-count/', views.unread_chat_count_view),
    path('api/chat/messages/<int:message_id>/delete/', views.delete_chat_message_view),

    path('api/push-subscriptions/', views.save_push_subscription_view),
    path('api/admin/signup-company/', views.signup_create_company_view, name='signup_create_company'),
    path('api/admin/invite/', views.invite_admin_view, name='invite_admin'),
    path('api/admin/invite/<str:token>/', views.verify_invite_view, name='verify_invite'),
    path('api/admin/accept-invite/', views.accept_invite_view, name='accept_invite'),

    # ── ATTENDANCE (GPS check-in / check-out) ───────────────────────
    path('api/attendance/office-location/', views.office_location_view),
    path('api/attendance/check-in/', views.attendance_check_in_view),
    path('api/attendance/check-out/', views.attendance_check_out_view),
    path('api/attendance/mine/', views.my_attendance_view),
    path('api/admin/attendance/today/', views.admin_attendance_today_view),
    path('api/admin/employees/<int:employee_id>/attendance/', views.admin_employee_attendance_view),

    # ── SUPERADMIN API ──────────────────────────────────────────────
    path('api/superadmin/dashboard-stats/', views.superadmin_dashboard_stats_view),
    path('api/superadmin/filter-options/', views.superadmin_filter_options_view),

    path('api/superadmin/companies/', views.superadmin_companies_view),
    path('api/superadmin/companies/create/', views.superadmin_create_company_view),
    path('api/superadmin/companies/<int:company_id>/', views.superadmin_company_detail_view),

    path('api/superadmin/employees/', views.superadmin_all_employees_view),
    path('api/superadmin/employees/<int:profile_id>/', views.superadmin_employee_detail_view),

    path('api/superadmin/work-entries/', views.superadmin_all_work_entries_view),
    path('api/superadmin/work-entries/<int:entry_id>/', views.superadmin_work_entry_detail_view),

    path('api/superadmin/tasks/', views.superadmin_all_tasks_view),
    path('api/superadmin/tasks/<int:task_id>/', views.superadmin_task_detail_view),

    path('api/superadmin/invites/', views.superadmin_all_invites_view),
    path('api/superadmin/invites/<int:invite_id>/', views.superadmin_invite_detail_view),

    path('api/superadmin/reports/', views.superadmin_all_reports_view),
    path('api/superadmin/reports/<int:report_id>/', views.superadmin_report_detail_view),

    path('api/superadmin/users/', views.superadmin_all_users_view),
    path('api/superadmin/users/create/', views.superadmin_create_user_view),
    path('api/superadmin/users/<int:user_id>/', views.superadmin_user_detail_view),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Frontend URL patterns - serve the vanilla JS app
frontend_patterns = [
    path('', TemplateView.as_view(template_name='index.html'), name='home'),
    path('employee-login/', TemplateView.as_view(template_name='employee-login.html'), name='employee_login'),
    path('admin-login/', TemplateView.as_view(template_name='admin-login.html'), name='admin_login'),

    # Test routes for base templates
    path('admin/test/', page_views.admin_test_view),
    path('employee/test/', page_views.employee_test_view),

    # Employee routes
    path('employee/', page_views.employee_worklog_view),
    path('employee/worklog/', page_views.employee_worklog_view),
    path('employee/submit-report/', page_views.employee_submit_report_view),
    path('employee/my-reports/', page_views.employee_my_reports_view),
    path('employee/profile/', page_views.employee_profile_view),
    path('employee/chat/', page_views.employee_chat_view),
    path('employee/chart/', page_views.employee_chart_view),
    path('employee/attendance/', page_views.employee_attendance_view),

    # Admin routes
    path('admin/', page_views.page_admin_worklog_view),
    path('admin/worklog/', page_views.page_admin_worklog_view),
    path('admin/all-reports/', page_views.page_admin_all_reports_view),
    path('admin/employees/', page_views.page_admin_employees_view),
    path('admin/analytics/', page_views.page_admin_analytics_view),
    path('admin/chat/', page_views.page_admin_chat_view),
    path('admin/profile/', page_views.page_admin_profile_view),
    path('admin/attendance/', page_views.page_admin_attendance_view),

    # ── SUPERADMIN PAGES (explicit paths — no catch-all regex) ──────
    path('superadmin/', TemplateView.as_view(template_name='superadmin/index.html')),
    path('superadmin/companies/', TemplateView.as_view(template_name='superadmin/companies.html')),
    path('superadmin/company-detail/', TemplateView.as_view(template_name='superadmin/Companydetail.html')),
    path('superadmin/employees/', TemplateView.as_view(template_name='superadmin/employees.html')),
    path('superadmin/work-entries/', TemplateView.as_view(template_name='superadmin/work-entries.html')),
    path('superadmin/tasks/', TemplateView.as_view(template_name='superadmin/tasks.html')),
    path('superadmin/invites/', TemplateView.as_view(template_name='superadmin/invites.html')),
    path('superadmin/users/', TemplateView.as_view(template_name='superadmin/users.html')),
]

urlpatterns += frontend_patterns + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)