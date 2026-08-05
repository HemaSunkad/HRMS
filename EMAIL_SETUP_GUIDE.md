# Email Setup Guide for WorkTrack

## Quick Setup (5 minutes)

### Step 1: Enable 2-Factor Authentication on your Google Account
1. Go to https://myaccount.google.com/security
2. Find "2-Step Verification" and turn it ON if not already enabled

### Step 2: Generate an App Password
1. Go to https://myaccount.google.com/apppasswords
2. Sign in if prompted
3. Select "Mail" and "Other (Custom name)"
4. Name it "WorkTrack" and click Generate
5. Copy the 16-character password (example: `abcd efgh ijkl mnop`)

### Step 3: Update .env File
Replace the placeholder values in `.env` with your actual credentials:

```bash
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-16-char-app-password
```

### Step 4: Restart Django Server
Stop and restart the server to apply the new settings.

## Verification

When the server starts, you should see:
```
[Email] Configured to send emails via your-email@gmail.com
```

If you see this instead, the credentials are not properly configured:
```
[Email] Using console backend - emails will be printed to console
```

## Testing

After configuration:
1. Add a new employee from the admin panel
2. Check the employee's email inbox for login credentials
3. Send a co-admin invite and verify the email is received

## Troubleshooting

**"Less secure app access" error:**
- Make sure you're using an App Password, NOT your regular password
- App Passwords only work with 2FA enabled

**Email not sending:**
- Verify the App Password was copied correctly (16 characters with spaces)
- Check that `EMAIL_HOST_USER` is your exact Gmail address

**Still seeing console backend:**
- Make sure there are no typos in the .env file
- The system detects and rejects placeholder values like `your-email@gmail.com`
