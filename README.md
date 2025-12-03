# Reconciliation Work Allocation App

A Flask-based application for managing reconciliation tasks with **role-based access control**.

## Features

- **User Roles**: Admin (full access) and User (view & complete only)
- **Frequency-Based Views**: Daily, Weekly, and Monthly reconciliations
- **Completion Tracking**: Log items reconciled, exceptions, and notes
- **Auto-scheduling**: Calculates next due date based on frequency
- **Overdue Alerts**: Dashboard highlights overdue items

## Reconciliation Frequencies

| Frequency | Schedule | Next Due Calculation |
|-----------|----------|---------------------|
| **Daily** | Every business day | Next working day (Mon-Fri) |
| **Weekly** | Once per week | **Monday** (1st working day of next week) |
| **Monthly** | Once per month | **1st working day** of next month |

## User Roles

| Role | Permissions |
|------|-------------|
| **Admin** | Add/Edit/Delete reconciliations, team members, users. Reset recs. Full access. |
| **User** | View all data. Start working on recs. Mark recs as complete. |

## Quick Start

### 1. Install Dependencies
```bash
pip install flask flask-sqlalchemy
```

### 2. Run the App
```bash
python app.py
```

### 3. Login
Open **http://127.0.0.1:5000** and login with:
- **Username:** `admin`
- **Password:** `admin123`

⚠️ **Change the default password immediately!**

## Data Storage Location

Your data is stored in an **SQLite database file**:

| Mode | Location |
|------|----------|
| **Development** | Same folder as `app.py` → `reconciliation.db` |
| **EXE (Windows)** | `C:\Users\<YourName>\ReconciliationApp\reconciliation.db` |

### Backup Your Data
Simply copy the `reconciliation.db` file to a safe location.

### Restore Data
Replace the `reconciliation.db` file and restart the app.

## Building the EXE

### On Windows:
```bash
pip install -r requirements.txt
pyinstaller --onefile --add-data "templates;templates" --name ReconciliationApp app.py
```

Your exe will be in the `dist` folder.

## Managing Users

1. Login as **admin**
2. Go to **Admin → Manage Users**
3. Add users with either **Admin** or **User** role

## Reconciliation Workflow

1. **Admin creates** reconciliations with frequency (Daily/Weekly/Monthly)
2. **Users view** the dashboard and assigned recs
3. **Users click "Complete"** to mark as done (logs items & exceptions)
4. **Admin resets** completed recs for the next cycle

## File Structure

```
reconciliation_app/
├── app.py              # Main application with role-based access
├── requirements.txt    # Dependencies
├── reconciliation.db   # SQLite database (created on first run)
└── templates/          # HTML templates
```

## Default Accounts

On first run, the app creates:
- **Username:** admin
- **Password:** admin123
- **Role:** Admin

Create additional users through the admin panel.
