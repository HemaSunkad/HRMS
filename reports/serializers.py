from rest_framework import serializers
from django.contrib.auth.models import User
from .models import EmployeeProfile, DailyReport

class EmployeeProfileSerializer(serializers.ModelSerializer):
    photo_url = serializers.SerializerMethodField()

    class Meta:
        model = EmployeeProfile
        fields = '__all__'

    def get_photo_url(self, obj):
        photo = getattr(obj, 'photo', None)
        if photo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(photo.url)
            return photo.url
        return None

class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    profile = serializers.SerializerMethodField()

    class Meta:                      # ← 4 spaces
        model = User                 # ← 8 spaces
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'full_name', 'profile', 'is_superuser']  # ← 8 spaces

    def get_full_name(self, obj):    # ← 4 spaces
        return obj.get_full_name()

    def get_profile(self, obj):
        try:
            p = obj.employeeprofile
        except EmployeeProfile.DoesNotExist:
            return {
                'employee_id': '',
                'department': '',
                'designation': '',
                'phone': '',
                'is_admin': False,
                'photo': None,
            }

        photo_url = None
        photo = getattr(p, 'photo', None)
        if photo:
            try:
                request = self.context.get('request')
                if request:
                    photo_url = request.build_absolute_uri(photo.url)
                else:
                    photo_url = f'http://127.0.0.1:8001{photo.url}'
            except Exception:
                photo_url = None

        return {
            'employee_id': p.employee_id,
            'department': p.department,
            'designation': p.designation,
            'phone': p.phone,
            'is_admin': p.is_admin,
            'photo': photo_url,
        }

class DailyReportSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    employee_department = serializers.SerializerMethodField()

    class Meta:
        model = DailyReport
        fields = '__all__'
        read_only_fields = ['employee', 'submitted_at', 'updated_at']

    def get_employee_name(self, obj):
        return obj.employee.get_full_name()

    def get_employee_department(self, obj):
        try:
            return obj.employee.employeeprofile.department
        except:
            return ''