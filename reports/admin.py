from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from .models import Company, AdminInvite, EmployeeProfile, WorkEntry, AssignedTask, DailyReport


class EmployeeProfileInline(admin.TabularInline):
    model = EmployeeProfile
    extra = 0
    fields = ('user', 'employee_id', 'department', 'designation', 'is_admin', 'is_owner')
    readonly_fields = ('user', 'employee_id')
    can_delete = False
    show_change_link = True


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'employee_count', 'admin_count', 'created_at', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)
    inlines = [EmployeeProfileInline]
    readonly_fields = ('view_related_data',)
    fields = ('name', 'is_active', 'created_at', 'view_related_data')
    readonly_fields = ('created_at', 'view_related_data')

    def employee_count(self, obj):
        return obj.employees.count()
    employee_count.short_description = 'Total People'

    def admin_count(self, obj):
        return obj.employees.filter(is_admin=True).count()
    admin_count.short_description = 'Admins'

    def view_related_data(self, obj):
        """
        Clickable buttons that jump straight into each dataset,
        already filtered to show ONLY this company's records.
        """
        if not obj.pk:
            return "Save the company first to see related data."

        links = [
            ('Employees', 'reports_employeeprofile_changelist', f'company__id__exact={obj.id}'),
            ('Admin Invites', 'reports_admininvite_changelist', f'company__id__exact={obj.id}'),
            ('Assigned Tasks', 'reports_assignedtask_changelist', f'assigned_to__employeeprofile__company__id__exact={obj.id}'),
            ('Work Entries', 'reports_workentry_changelist', f'employee__employeeprofile__company__id__exact={obj.id}'),
            ('Daily Reports', 'reports_dailyreport_changelist', f'employee__employeeprofile__company__id__exact={obj.id}'),
        ]

        html = '<div style="display:flex; gap:10px; flex-wrap:wrap;">'
        for label, url_name, query in links:
            url = reverse(f'admin:{url_name}') + f'?{query}'
            html += (
                f'<a href="{url}" style="padding:8px 14px; background:#417690; '
                f'color:white; border-radius:6px; text-decoration:none; font-weight:bold;">'
                f'{label} →</a>'
            )
        html += '</div>'
        return format_html(html)
    view_related_data.short_description = 'View this company\'s data'


@admin.register(EmployeeProfile)
class EmployeeProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'company', 'employee_id', 'department', 'designation', 'is_admin', 'is_owner')
    list_filter = ('company', 'is_admin', 'is_owner', 'department')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'employee_id')


@admin.register(AdminInvite)
class AdminInviteAdmin(admin.ModelAdmin):
    list_display = ('email', 'company', 'invited_by', 'accepted', 'created_at', 'expires_at')
    list_filter = ('company', 'accepted')
    search_fields = ('email',)


@admin.register(WorkEntry)
class WorkEntryAdmin(admin.ModelAdmin):
    list_display = ('employee', 'get_company', 'project_name', 'date', 'status', 'review_status')
    list_filter = ('employee__employeeprofile__company', 'status', 'review_status')
    search_fields = ('project_name', 'employee__email')

    def get_company(self, obj):
        try:
            return obj.employee.employeeprofile.company
        except Exception:
            return '—'
    get_company.short_description = 'Company'


@admin.register(AssignedTask)
class AssignedTaskAdmin(admin.ModelAdmin):
    list_display = ('assigned_to', 'get_company', 'project_name', 'status', 'deadline')
    list_filter = ('assigned_to__employeeprofile__company', 'status')
    search_fields = ('project_name', 'assigned_to__email')

    def get_company(self, obj):
        try:
            return obj.assigned_to.employeeprofile.company
        except Exception:
            return '—'
    get_company.short_description = 'Company'


@admin.register(DailyReport)
class DailyReportAdmin(admin.ModelAdmin):
    list_display = ('employee', 'get_company', 'status', 'date')
    list_filter = ('employee__employeeprofile__company', 'status')

    def get_company(self, obj):
        try:
            return obj.employee.employeeprofile.company
        except Exception:
            return '—'
    get_company.short_description = 'Company'