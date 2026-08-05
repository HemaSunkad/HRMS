# WorkTrack - Work Management System

A complete work management system with time tracking, reporting, and team collaboration features.

## 🏗️ Architecture

- **Backend**: Django REST Framework (Python)
- **Frontend**: Vanilla HTML, CSS, JavaScript (No frameworks)
- **Database**: SQLite (development), can be upgraded to PostgreSQL for production

## 📁 Project Structure

```
worktrack-backend/
├── manage.py           # Django management script
├── db.sqlite3          # SQLite database
├── static/              # Static files (CSS, JS, assets)
│   ├── css/           # Stylesheets
│   ├── js/            # JavaScript modules
│   └── assets/        # Images and fonts
├── templates/          # HTML templates
│   ├── employee/      # Employee portal pages
│   ├── admin/         # Admin portal pages
│   └── superadmin/    # Superadmin pages
└── worktrack/         # Django app
    ├── settings.py    # Django settings
    ├── urls.py        # URL configuration
    └── reports/       # API views and models
```

## 🚀 Quick Start

### Prerequisites

- Python 3.9 or higher
- pip (Python package manager)
- Git (optional, for cloning)

### Installation Steps

#### 1. Navigate to the Project Directory

```bash
cd worktrack-backend
```

#### 2. Create a Virtual Environment

**Windows (Git Bash/PowerShell):**
```bash
python -m venv venv
source venv/Scripts/activate  # Git Bash
# OR
venv\Scripts\activate         # PowerShell
```

**Linux/Mac:**
```bash
python3 -m venv venv
source venv/bin/activate
```

#### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

If `requirements.txt` doesn't exist, install the core dependencies:

```bash
pip install django djangorestframework django-cors-headers python-dotenv
```

#### 4. Configure Environment Variables

Create a `.env` file in the `worktrack-backend` directory:

```bash
# Copy the example file
cp .env.example .env
```

Edit `.env` with your settings:
```env
SECRET_KEY=your-secret-key-here
DEBUG=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
GOOGLE_CLIENT_ID=your-google-client-id
ADMIN_SECURITY_CODE=your-admin-code
```

#### 5. Run Database Migrations

```bash
python manage.py migrate
```

#### 6. Create a Superuser (Optional)

For accessing Django admin panel:
```bash
python manage.py createsuperuser
```

#### 7. Populate Initial Data (Optional)

If you have a `populated.py` script:
```bash
python populated.py
```

#### 8. Collect Static Files

```bash
python manage.py collectstatic --noinput
```

### 🎯 Running the Application

#### Development Mode

```bash
python manage.py runserver
```

The application will be available at:
- **Main App**: http://localhost:8000
- **API Endpoints**: http://localhost:8000/api/
- **Django Admin**: http://localhost:8000/admin/

#### Production Mode

For production deployment, use a proper WSGI server like Gunicorn:

```bash
pip install gunicorn
gunicorn worktrack.wsgi:application --bind 0.0.0.0:8000
```

## 👤 Default Access

### Initial Setup

The application comes with default users for testing:

**Employee:**
- Email: `employee@test.com`
- Password: `password123`

**Admin:**
- Email: `admin@test.com`
- Password: `admin123`

**Superadmin:**
- Email: `super@test.com`
- Password: `super123`

**Note:** Change these passwords after first login!

## 📱 Application Features

### Employee Portal (`/employee/`)
- 📝 **Work Log**: Track daily work entries with start/stop timers
- 📊 **Submit Reports**: Daily progress reports with tasks, blockers, and comments
- 📋 **My Reports**: View and manage submitted reports
- 👤 **Profile**: Update personal information and change password
- 💬 **Chat**: Team communication with real-time messaging

### Admin Portal (`/admin/`)
- 👥 **Team Management**: View all team members' work logs
- ✅ **Review Entries**: Approve/reject work entries
- 📋 **Reports Review**: Review and provide feedback on daily reports
- 📊 **Analytics**: Team performance metrics and insights
- 💬 **Chat**: Admin communication channels
- ➕ **Assign Tasks**: Delegate tasks to team members

### Superadmin Portal (`/superadmin/`)
- 🏢 **Company Management**: Manage multiple company workspaces
- 👥 **All Employees**: View employees across all companies
- 📊 **Global Analytics**: Platform-wide statistics
- 📧 **Invites**: Manage admin invitations

## 🔧 Configuration

### CORS Settings

The backend is configured to allow requests from:
- `http://localhost:3000` (React development)
- `http://localhost:8000` (Django development)
- `http://127.0.0.1:8000`

### Email Configuration

Update in `.env`:
```env
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
```

For Gmail, use an [App Password](https://support.google.com/accounts/answer/185833).

### Database Configuration

Default uses SQLite. To use PostgreSQL:

```python
# In settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'worktrack',
        'USER': 'your-user',
        'PASSWORD': 'your-password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

Then install:
```bash
pip install psycopg2-binary
```

## 🐛 Troubleshooting

### Port Already in Use

If port 8000 is already in use:
```bash
python manage.py runserver 8001
```

### Static Files Not Loading

Run:
```bash
python manage.py collectstatic --noinput --clear
```

### Database Issues

Reset the database:
```bash
rm db.sqlite3
python manage.py migrate
python populated.py  # If available
```

### CORS Errors

Check your IP and update CORS settings in `settings.py`:
```python
CORS_ALLOWED_ORIGINS = [
    "http://your-ip:8000",
]
```

## 🔒 Security Notes

1. **Change Default Passwords**: Update all default user passwords
2. **Set Strong SECRET_KEY**: Generate a random secret key for production
3. **DEBUG=False**: Set `DEBUG=False` in production
4. **HTTPS**: Use HTTPS in production
5. **Firewall**: Configure firewall rules for production

## 📊 API Endpoints

### Authentication
- `POST /api/login/` - User login
- `POST /api/register/` - User registration
- `POST /api/logout/` - User logout
- `GET /api/me/` - Get current user info

### Employee
- `GET /api/employee/entries/` - Get work entries
- `POST /api/employee/entries/` - Create work entry
- `GET /api/reports/` - Get user reports
- `POST /api/reports/` - Submit report

### Admin
- `GET /api/admin/employees/` - Get all employees
- `GET /api/admin/reports/` - Get all reports
- `POST /api/admin/reports/<id>/review/` - Review report
- `POST /api/admin/assign-task/` - Assign task

### Chat
- `GET /api/chat/rooms/` - Get chat rooms
- `POST /api/chat/rooms/dm/` - Create DM room
- `GET /api/chat/rooms/<id>/messages/` - Get messages
- `POST /api/chat/send-message/` - Send message

## 📝 Development

### Adding New Features

1. **Backend**: Add views in `worktrack/reports/views.py`
2. **URLs**: Register in `worktrack/urls.py`
3. **Frontend**: Update JavaScript in `static/js/api.js`
4. **Pages**: Create HTML in `templates/`

### Testing

```bash
# Run Django tests
python manage.py test

# Check for issues
python manage.py check
```

## 🚀 Deployment

### PythonAnywhere

1. Upload code to PythonAnywhere
2. Configure virtual environment
3. Install dependencies
4. Configure WSGI file
5. Set up static files

### Docker (Optional)

Create `Dockerfile`:
```dockerfile
FROM python:3.9
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["gunicorn", "worktrack.wsgi:application", "--bind", "0.0.0.0:8000"]
```

## 📄 License

This project is proprietary software.

## 🆘 Support

For issues and questions, contact the development team.

---

**Built with ❤️ using Django + Vanilla JavaScript**
