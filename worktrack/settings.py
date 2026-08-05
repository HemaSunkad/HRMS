from pathlib import Path
import os
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / '.env')

SECRET_KEY = os.getenv('SECRET_KEY')

DEBUG = True
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin-allow-popups"
ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'reports',
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'worktrack.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'worktrack.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
# Allow chat attachments up to 25MB (Django's default is 2.5MB)
DATA_UPLOAD_MAX_MEMORY_SIZE = 26214400  # 25 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 26214400  # 25 MB
AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]
STATIC_ROOT = BASE_DIR / 'staticfiles'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# In development, serve static files straight off disk (no manifest, no
# collectstatic needed, no stale cached copies). In production, use the
# hashed/compressed manifest storage for cache-busting + gzip/brotli.
if DEBUG:
    STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"
else:
    STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

CORS_ALLOW_CREDENTIALS = True

CORS_ALLOWED_ORIGINS = [
    "https://hrms.haegl.in",
    "http://localhost:3000",
]
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

# Email Settings
# Use console backend for development if email credentials are not configured
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')

# Check if email credentials are properly configured (not placeholder values)
if (EMAIL_HOST_USER and EMAIL_HOST_PASSWORD and
    EMAIL_HOST_USER != 'your-email@gmail.com' and
    EMAIL_HOST_PASSWORD != 'your-app-password-here'):
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = 'smtp.gmail.com'
    EMAIL_PORT = 587
    EMAIL_USE_TLS = True
    DEFAULT_FROM_EMAIL = f'WorkTrack <{EMAIL_HOST_USER}>'
    print(f'[Email] Configured to send emails via {EMAIL_HOST_USER}')
else:
    # Fallback to console backend for development
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    EMAIL_HOST_USER = 'console@example.com'
    EMAIL_HOST_PASSWORD = 'console'
    DEFAULT_FROM_EMAIL = 'WorkTrack <console@example.com>'
    print('[Email] Using console backend - emails will be printed to console')

EMAIL_TIMEOUT = 30

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
ADMIN_SECURITY_CODE = os.getenv('ADMIN_SECURITY_CODE')

VAPID_PRIVATE_KEY_PATH = str(BASE_DIR / 'private_key.pem')
VAPID_CLAIMS = {
    "sub": "mailto:hemasunkad052@gmail.com"
}
FRONTEND_URL = os.getenv('FRONTEND_URL', 'https://hrms.haegl.in/')