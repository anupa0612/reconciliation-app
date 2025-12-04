"""
Reconciliation Work Allocation App with Role-Based Access Control
- Admin: Full access (add/edit/delete)
- User: View and mark completion only
"""
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime, date, timedelta, timezone
import os
import sys
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Sri Lanka timezone (UTC+5:30)
SL_OFFSET = timedelta(hours=5, minutes=30)

# Email Configuration (Outlook/Office 365)
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.office365.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USER = os.environ.get('EMAIL_USER', '')  # Your Outlook email
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD', '')  # Your Outlook password or app password
EMAIL_FROM = os.environ.get('EMAIL_FROM', '')  # From email address

# Handle PyInstaller bundling
if getattr(sys, 'frozen', False):
    template_folder = os.path.join(sys._MEIPASS, 'templates')
    static_folder = os.path.join(sys._MEIPASS, 'static')
    app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
    # EXE: Data stored in user's home folder
    app_data = os.path.join(os.path.expanduser('~'), 'ReconciliationApp')
    os.makedirs(app_data, exist_ok=True)
    db_path = os.path.join(app_data, 'reconciliation.db')
    database_url = f'sqlite:///{db_path}'
    print(f"\n[DATA LOCATION] Database stored at: {db_path}")
else:
    app = Flask(__name__)
    # Check for Railway/Cloud DATABASE_URL first, otherwise use local SQLite
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        # Railway uses postgres://, SQLAlchemy needs postgresql+psycopg://
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql+psycopg://', 1)
        elif database_url.startswith('postgresql://'):
            database_url = database_url.replace('postgresql://', 'postgresql+psycopg://', 1)
        db_path = "Cloud PostgreSQL Database"
        print(f"\n[DATABASE] Using cloud PostgreSQL database")
    else:
        # Local development: use SQLite
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'reconciliation.db')
        database_url = f'sqlite:///{db_path}'
        print(f"\n[DATA LOCATION] Database stored at: {db_path}")

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Template filter to convert UTC to Sri Lanka time
@app.template_filter('local_time')
def local_time_filter(utc_dt):
    if utc_dt is None:
        return ''
    local_dt = utc_dt + SL_OFFSET
    return local_dt.strftime('%Y-%m-%d %H:%M')

@app.template_filter('local_date')
def local_date_filter(utc_dt):
    if utc_dt is None:
        return ''
    local_dt = utc_dt + SL_OFFSET
    return local_dt.strftime('%Y-%m-%d')

# ============== DATABASE MODELS ==============

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user')  # 'admin' or 'user'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        return self.role == 'admin'

class TeamMember(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    role = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    reconciliations = db.relationship('Reconciliation', backref='assignee', lazy=True)

class Reconciliation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    frequency = db.Column(db.String(20), nullable=False)
    priority = db.Column(db.String(20), default='Medium')
    status = db.Column(db.String(20), default='Pending')
    source_system = db.Column(db.String(100))
    target_system = db.Column(db.String(100))
    due_date = db.Column(db.Date)
    due_time = db.Column(db.String(5), default='17:00')  # Format: HH:MM (24-hour) - for Daily only
    last_completed = db.Column(db.DateTime)
    next_due = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    assigned_to = db.Column(db.Integer, db.ForeignKey('team_member.id'))
    completion_notes = db.Column(db.Text)
    items_reconciled = db.Column(db.Integer, default=0)
    exceptions_found = db.Column(db.Integer, default=0)
    completed_by = db.Column(db.String(100))
    overdue_notified = db.Column(db.Boolean, default=False)  # Track if overdue email was sent
    
    def is_overdue(self):
        """Check if reconciliation is overdue based on date and time"""
        if self.status == 'Completed' or not self.due_date:
            return False
        
        today = date.today()
        now = datetime.utcnow() + SL_OFFSET  # Current time in Sri Lanka
        
        if self.due_date < today:
            return True
        elif self.due_date == today:
            # For Daily recs, check due time
            if self.frequency == 'Daily' and self.due_time:
                try:
                    due_hour, due_min = map(int, self.due_time.split(':'))
                    if now.hour > due_hour or (now.hour == due_hour and now.minute > due_min):
                        return True
                except:
                    pass
            # For Weekly/Monthly, overdue at end of day (11:59 PM)
            elif self.frequency in ['Weekly', 'Monthly']:
                if now.hour >= 23 and now.minute >= 59:
                    return True
        return False
    
    def is_due_today(self):
        """Check if reconciliation is due today but not yet overdue"""
        if self.status == 'Completed' or not self.due_date:
            return False
        return self.due_date == date.today() and not self.is_overdue()
    
    @staticmethod
    def get_last_working_day_of_week(reference_date=None):
        """Get last working day (Friday) of the current week"""
        if reference_date is None:
            reference_date = date.today()
        # Find Friday of this week
        days_until_friday = 4 - reference_date.weekday()
        if days_until_friday < 0:
            days_until_friday += 7
        friday = reference_date + timedelta(days=days_until_friday)
        return friday
    
    @staticmethod
    def get_next_last_working_day_of_week():
        """Get last working day (Friday) of next week"""
        today = date.today()
        # Find Friday of next week
        days_until_friday = 4 - today.weekday()
        if days_until_friday <= 0:
            days_until_friday += 7
        next_friday = today + timedelta(days=days_until_friday)
        # If today is Friday or past Friday, go to next week's Friday
        if today.weekday() >= 4:
            next_friday += timedelta(days=7)
        return next_friday
    
    def calculate_next_due(self):
        today = date.today()
        if self.frequency == 'Daily':
            # Next business day (skip weekends)
            next_day = today + timedelta(days=1)
            while next_day.weekday() >= 5:  # Saturday=5, Sunday=6
                next_day += timedelta(days=1)
            return next_day
        elif self.frequency == 'Weekly':
            # Last working day of next week (Friday)
            return self.get_next_last_working_day_of_week()
        elif self.frequency == 'Monthly':
            # 1st working day of next month
            month = today.month + 1
            year = today.year
            if month > 12:
                month = 1
                year += 1
            first_of_month = date(year, month, 1)
            # If 1st is Saturday, move to Monday (3rd)
            # If 1st is Sunday, move to Monday (2nd)
            while first_of_month.weekday() >= 5:
                first_of_month += timedelta(days=1)
            return first_of_month
        return today

# ============== EMAIL FUNCTIONS ==============

def send_overdue_email(rec, assigned_member, admin_emails):
    """Send overdue notification email via Outlook"""
    if not EMAIL_USER or not EMAIL_PASSWORD:
        print("[EMAIL] Email not configured. Skipping notification.")
        return False
    
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = EMAIL_FROM or EMAIL_USER
        msg['To'] = assigned_member.email
        msg['Cc'] = ', '.join(admin_emails)
        msg['Subject'] = f'OVERDUE: {rec.name} - Reconciliation Past Due'
        
        # Email body
        body = f"""
Dear {assigned_member.name},

This is an automated notification to inform you that the following reconciliation is now OVERDUE:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RECONCILIATION DETAILS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Name: {rec.name}
Frequency: {rec.frequency}
Priority: {rec.priority}
Due Date: {rec.due_date.strftime('%Y-%m-%d') if rec.due_date else 'Not set'}
{f"Due Time: {rec.due_time}" if rec.frequency == 'Daily' and rec.due_time else ""}
Source System: {rec.source_system or 'N/A'}
Target System: {rec.target_system or 'N/A'}

Status: OVERDUE

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Please complete this reconciliation as soon as possible and contact your administrator.

Note: Only an administrator can mark overdue items as completed.

Best regards,
ReconcileHub System

---
This is an automated message. Please do not reply directly to this email.
"""
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Send email
        all_recipients = [assigned_member.email] + admin_emails
        
        server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_USER, all_recipients, msg.as_string())
        server.quit()
        
        print(f"[EMAIL] Overdue notification sent for: {rec.name}")
        return True
        
    except Exception as e:
        print(f"[EMAIL ERROR] Failed to send email: {str(e)}")
        return False

def check_and_notify_overdue():
    """Check for overdue items and send notifications"""
    with app.app_context():
        # Get all overdue reconciliations that haven't been notified
        overdue_recs = Reconciliation.query.filter(
            Reconciliation.status != 'Completed',
            Reconciliation.overdue_notified == False
        ).all()
        
        # Filter to actually overdue items
        overdue_recs = [r for r in overdue_recs if r.is_overdue()]
        
        if not overdue_recs:
            return
        
        # Get all admin emails
        admins = User.query.filter_by(role='admin').all()
        admin_emails = [a.username + '@' for a in admins if a.username]  # Modify as needed
        
        for rec in overdue_recs:
            if rec.assignee and rec.assignee.email:
                # Send notification
                if send_overdue_email(rec, rec.assignee, admin_emails):
                    rec.overdue_notified = True
                    db.session.commit()

# ============== ACCESS CONTROL ==============

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        user = User.query.get(session['user_id'])
        if not user or not user.is_admin():
            flash('You do not have permission to perform this action. Admin access required.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def get_current_user():
    if 'user_id' in session:
        return User.query.get(session['user_id'])
    return None

@app.context_processor
def inject_user():
    return dict(current_user=get_current_user())

# ============== AUTH ROUTES ==============

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            session['user_id'] = user.id
            flash(f'Welcome back, {user.name}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current_user = get_current_user()
        old_password = request.form['old_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        
        if not current_user.check_password(old_password):
            flash('Current password is incorrect.', 'error')
        elif new_password != confirm_password:
            flash('New passwords do not match.', 'error')
        elif len(new_password) < 4:
            flash('Password must be at least 4 characters.', 'error')
        else:
            current_user.set_password(new_password)
            db.session.commit()
            flash('Password changed successfully!', 'success')
            return redirect(url_for('dashboard'))
    
    return render_template('change_password.html')

# ============== USER MANAGEMENT (Admin Only) ==============

@app.route('/users')
@admin_required
def list_users():
    users = User.query.all()
    return render_template('users.html', users=users)

@app.route('/users/add', methods=['GET', 'POST'])
@admin_required
def add_user():
    if request.method == 'POST':
        username = request.form['username']
        name = request.form['name']
        password = request.form['password']
        role = request.form['role']
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists!', 'error')
            return redirect(url_for('add_user'))
        
        user = User(username=username, name=name, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash(f'User "{name}" created successfully!', 'success')
        return redirect(url_for('list_users'))
    
    return render_template('add_user.html')

@app.route('/users/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
def edit_user(id):
    user = User.query.get_or_404(id)
    if request.method == 'POST':
        user.name = request.form['name']
        user.role = request.form['role']
        if request.form.get('password'):
            user.set_password(request.form['password'])
        db.session.commit()
        flash(f'User "{user.name}" updated successfully!', 'success')
        return redirect(url_for('list_users'))
    
    return render_template('edit_user.html', user=user)

@app.route('/users/delete/<int:id>')
@admin_required
def delete_user(id):
    user = User.query.get_or_404(id)
    if user.id == session['user_id']:
        flash('You cannot delete your own account!', 'error')
        return redirect(url_for('list_users'))
    db.session.delete(user)
    db.session.commit()
    flash(f'User "{user.name}" deleted successfully!', 'success')
    return redirect(url_for('list_users'))

# ============== DASHBOARD ==============

@app.route('/')
@login_required
def dashboard():
    today = date.today()
    
    total_members = TeamMember.query.count()
    total_recs = Reconciliation.query.count()
    
    daily_recs = Reconciliation.query.filter_by(frequency='Daily').count()
    weekly_recs = Reconciliation.query.filter_by(frequency='Weekly').count()
    monthly_recs = Reconciliation.query.filter_by(frequency='Monthly').count()
    
    pending_recs = Reconciliation.query.filter_by(status='Pending').count()
    in_progress_recs = Reconciliation.query.filter_by(status='In Progress').count()
    completed_recs = Reconciliation.query.filter_by(status='Completed').count()
    on_hold_recs = Reconciliation.query.filter_by(status='On Hold').count()
    
    due_today = Reconciliation.query.filter(
        Reconciliation.due_date == today,
        Reconciliation.status != 'Completed'
    ).all()
    
    overdue = Reconciliation.query.filter(
        Reconciliation.due_date < today,
        Reconciliation.status != 'Completed'
    ).all()
    
    members = TeamMember.query.all()
    workload = []
    for member in members:
        active_recs = Reconciliation.query.filter(
            Reconciliation.assigned_to == member.id,
            Reconciliation.status.in_(['Pending', 'In Progress'])
        ).count()
        workload.append({'member': member, 'active_recs': active_recs})
    
    recent_completed = Reconciliation.query.filter_by(status='Completed').order_by(
        Reconciliation.last_completed.desc()
    ).limit(5).all()
    
    return render_template('dashboard.html',
                         total_members=total_members, total_recs=total_recs,
                         daily_recs=daily_recs, weekly_recs=weekly_recs, monthly_recs=monthly_recs,
                         pending_recs=pending_recs, in_progress_recs=in_progress_recs,
                         completed_recs=completed_recs, on_hold_recs=on_hold_recs,
                         due_today=due_today, overdue=overdue,
                         workload=workload, recent_completed=recent_completed, today=today)

# ============== TEAM MEMBER ROUTES ==============

@app.route('/members')
@login_required
def list_members():
    members = TeamMember.query.all()
    return render_template('members.html', members=members)

@app.route('/members/add', methods=['GET', 'POST'])
@admin_required
def add_member():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        role = request.form['role']
        
        if TeamMember.query.filter_by(email=email).first():
            flash('Email already exists!', 'error')
            return redirect(url_for('add_member'))
        
        member = TeamMember(name=name, email=email, role=role)
        db.session.add(member)
        db.session.commit()
        flash(f'Team member "{name}" added successfully!', 'success')
        return redirect(url_for('list_members'))
    
    return render_template('add_member.html')

@app.route('/members/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
def edit_member(id):
    member = TeamMember.query.get_or_404(id)
    if request.method == 'POST':
        member.name = request.form['name']
        member.email = request.form['email']
        member.role = request.form['role']
        db.session.commit()
        flash(f'Team member "{member.name}" updated successfully!', 'success')
        return redirect(url_for('list_members'))
    
    return render_template('edit_member.html', member=member)

@app.route('/members/delete/<int:id>')
@admin_required
def delete_member(id):
    member = TeamMember.query.get_or_404(id)
    Reconciliation.query.filter_by(assigned_to=id).update({'assigned_to': None})
    db.session.delete(member)
    db.session.commit()
    flash(f'Team member "{member.name}" deleted successfully!', 'success')
    return redirect(url_for('list_members'))

# ============== RECONCILIATION ROUTES ==============

@app.route('/reconciliations')
@login_required
def list_reconciliations():
    status_filter = request.args.get('status', '')
    frequency_filter = request.args.get('frequency', '')
    priority_filter = request.args.get('priority', '')
    member_filter = request.args.get('member', '')
    
    query = Reconciliation.query
    
    if status_filter:
        query = query.filter_by(status=status_filter)
    if frequency_filter:
        query = query.filter_by(frequency=frequency_filter)
    if priority_filter:
        query = query.filter_by(priority=priority_filter)
    if member_filter:
        query = query.filter_by(assigned_to=int(member_filter))
    
    recs = query.order_by(Reconciliation.due_date.asc()).all()
    members = TeamMember.query.all()
    today = date.today()
    
    return render_template('reconciliations.html', recs=recs, members=members,
                         status_filter=status_filter, frequency_filter=frequency_filter,
                         priority_filter=priority_filter, member_filter=member_filter, today=today)

@app.route('/reconciliations/add', methods=['GET', 'POST'])
@admin_required
def add_reconciliation():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form.get('description', '')
        frequency = request.form['frequency']
        priority = request.form['priority']
        source_system = request.form.get('source_system', '')
        target_system = request.form.get('target_system', '')
        assigned_to = request.form.get('assigned_to')
        
        # Handle due date/time based on frequency
        due_date = None
        due_time = '17:00'  # Default
        
        if frequency == 'Daily':
            # Auto-set due date to next working day, user provides due time
            today = date.today()
            due_date = today
            if today.weekday() >= 5:  # Weekend
                due_date = today + timedelta(days=(7 - today.weekday()))
            due_time = request.form.get('due_time', '17:00')
            
        elif frequency == 'Weekly':
            # Auto-set due date to last working day of week (Friday)
            due_date = Reconciliation.get_last_working_day_of_week()
            due_time = None  # Not used for weekly
            
        elif frequency == 'Monthly':
            # User provides due date
            due_date_str = request.form.get('due_date')
            due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date() if due_date_str else None
            due_time = None  # Not used for monthly
        
        rec = Reconciliation(
            name=name, description=description, frequency=frequency,
            priority=priority, source_system=source_system, target_system=target_system,
            assigned_to=int(assigned_to) if assigned_to else None, 
            due_date=due_date, due_time=due_time
        )
        db.session.add(rec)
        db.session.commit()
        flash(f'Reconciliation "{name}" created successfully!', 'success')
        return redirect(url_for('list_reconciliations'))
    
    members = TeamMember.query.all()
    today = date.today()
    next_friday = Reconciliation.get_last_working_day_of_week()
    return render_template('add_reconciliation.html', members=members, today=today, next_friday=next_friday)

@app.route('/reconciliations/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
def edit_reconciliation(id):
    rec = Reconciliation.query.get_or_404(id)
    if request.method == 'POST':
        rec.name = request.form['name']
        rec.description = request.form.get('description', '')
        old_frequency = rec.frequency
        rec.frequency = request.form['frequency']
        rec.priority = request.form['priority']
        rec.status = request.form['status']
        rec.source_system = request.form.get('source_system', '')
        rec.target_system = request.form.get('target_system', '')
        assigned_to = request.form.get('assigned_to')
        rec.assigned_to = int(assigned_to) if assigned_to else None
        
        # Handle due date/time based on frequency
        if rec.frequency == 'Daily':
            rec.due_time = request.form.get('due_time', '17:00')
            # Only recalculate due date if frequency changed
            if old_frequency != 'Daily':
                today = date.today()
                rec.due_date = today
                if today.weekday() >= 5:
                    rec.due_date = today + timedelta(days=(7 - today.weekday()))
        elif rec.frequency == 'Weekly':
            rec.due_time = None
            # Only recalculate due date if frequency changed
            if old_frequency != 'Weekly':
                rec.due_date = Reconciliation.get_last_working_day_of_week()
        elif rec.frequency == 'Monthly':
            rec.due_time = None
            due_date_str = request.form.get('due_date')
            rec.due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date() if due_date_str else None
        
        db.session.commit()
        flash(f'Reconciliation "{rec.name}" updated successfully!', 'success')
        return redirect(url_for('list_reconciliations'))
    
    members = TeamMember.query.all()
    today = date.today()
    next_friday = Reconciliation.get_last_working_day_of_week()
    return render_template('edit_reconciliation.html', rec=rec, members=members, today=today, next_friday=next_friday)

@app.route('/reconciliations/delete/<int:id>')
@admin_required
def delete_reconciliation(id):
    rec = Reconciliation.query.get_or_404(id)
    db.session.delete(rec)
    db.session.commit()
    flash(f'Reconciliation "{rec.name}" deleted successfully!', 'success')
    return redirect(url_for('list_reconciliations'))

@app.route('/reconciliations/view/<int:id>')
@login_required
def view_reconciliation(id):
    rec = Reconciliation.query.get_or_404(id)
    return render_template('view_reconciliation.html', rec=rec)

@app.route('/reconciliations/complete/<int:id>', methods=['GET', 'POST'])
@login_required
def complete_reconciliation(id):
    rec = Reconciliation.query.get_or_404(id)
    current_user = get_current_user()
    
    # If overdue, only admin can complete
    if rec.is_overdue() and not current_user.is_admin():
        flash('This reconciliation is overdue. Only an administrator can mark it as complete.', 'error')
        return redirect(url_for('list_reconciliations'))
    
    if request.method == 'POST':
        rec.status = 'Completed'
        rec.last_completed = datetime.utcnow()
        rec.items_reconciled = int(request.form.get('items_reconciled', 0))
        rec.exceptions_found = int(request.form.get('exceptions_found', 0))
        rec.completion_notes = request.form.get('completion_notes', '')
        rec.completed_by = current_user.name if current_user else 'Unknown'
        rec.next_due = rec.calculate_next_due()
        rec.overdue_notified = False  # Reset for next cycle
        db.session.commit()
        flash(f'Reconciliation "{rec.name}" marked as complete!', 'success')
        return redirect(url_for('list_reconciliations'))
    
    return render_template('complete_reconciliation.html', rec=rec)

@app.route('/reconciliations/start/<int:id>')
@login_required
def start_reconciliation(id):
    rec = Reconciliation.query.get_or_404(id)
    rec.status = 'In Progress'
    db.session.commit()
    flash(f'Started working on "{rec.name}"!', 'success')
    return redirect(request.referrer or url_for('list_reconciliations'))

@app.route('/reconciliations/status/<int:id>/<status>')
@login_required
def update_rec_status(id, status):
    rec = Reconciliation.query.get_or_404(id)
    rec.status = status
    db.session.commit()
    flash(f'Reconciliation "{rec.name}" status updated to {status}!', 'success')
    return redirect(url_for('list_reconciliations'))

@app.route('/reconciliations/reset/<int:id>')
@admin_required
def reset_reconciliation(id):
    rec = Reconciliation.query.get_or_404(id)
    rec.status = 'Pending'
    rec.due_date = rec.next_due or rec.calculate_next_due()
    rec.items_reconciled = 0
    rec.exceptions_found = 0
    rec.completion_notes = ''
    rec.completed_by = None
    rec.overdue_notified = False  # Reset notification flag
    db.session.commit()
    flash(f'Reconciliation "{rec.name}" reset for next cycle!', 'success')
    return redirect(url_for('list_reconciliations'))

@app.route('/reconciliations/notify/<int:id>')
@admin_required
def send_notification(id):
    """Manually send overdue notification for a specific reconciliation"""
    rec = Reconciliation.query.get_or_404(id)
    
    if not rec.is_overdue():
        flash('This reconciliation is not overdue.', 'error')
        return redirect(url_for('list_reconciliations'))
    
    if not rec.assignee:
        flash('No team member assigned to this reconciliation.', 'error')
        return redirect(url_for('list_reconciliations'))
    
    # Get admin emails
    admins = User.query.filter_by(role='admin').all()
    admin_emails = [a.username for a in admins if '@' in a.username]
    
    if send_overdue_email(rec, rec.assignee, admin_emails):
        rec.overdue_notified = True
        db.session.commit()
        flash(f'Overdue notification sent for "{rec.name}"!', 'success')
    else:
        flash('Failed to send notification. Check email configuration.', 'error')
    
    return redirect(url_for('list_reconciliations'))

@app.route('/api/check-overdue')
def api_check_overdue():
    """API endpoint to check and notify overdue items (can be called by scheduler)"""
    # Get all overdue reconciliations that haven't been notified
    all_recs = Reconciliation.query.filter(
        Reconciliation.status != 'Completed',
        Reconciliation.overdue_notified == False
    ).all()
    
    # Filter to actually overdue items
    overdue_recs = [r for r in all_recs if r.is_overdue()]
    
    if not overdue_recs:
        return jsonify({'status': 'ok', 'message': 'No new overdue items', 'count': 0})
    
    # Get all admin emails
    admins = User.query.filter_by(role='admin').all()
    admin_emails = [a.username for a in admins if '@' in a.username]
    
    notified_count = 0
    for rec in overdue_recs:
        if rec.assignee and rec.assignee.email:
            if send_overdue_email(rec, rec.assignee, admin_emails):
                rec.overdue_notified = True
                notified_count += 1
    
    db.session.commit()
    return jsonify({'status': 'ok', 'message': f'Sent {notified_count} notifications', 'count': notified_count})

# ============== FREQUENCY VIEWS ==============

@app.route('/daily')
@login_required
def daily_view():
    today = date.today()
    daily_recs = Reconciliation.query.filter_by(frequency='Daily').order_by(Reconciliation.status.asc()).all()
    members = TeamMember.query.all()
    return render_template('frequency_view.html', recs=daily_recs, members=members, today=today,
                         frequency='Daily', title='Daily Reconciliations')

@app.route('/weekly')
@login_required
def weekly_view():
    today = date.today()
    weekly_recs = Reconciliation.query.filter_by(frequency='Weekly').order_by(Reconciliation.due_date.asc()).all()
    members = TeamMember.query.all()
    return render_template('frequency_view.html', recs=weekly_recs, members=members, today=today,
                         frequency='Weekly', title='Weekly Reconciliations')

@app.route('/monthly')
@login_required
def monthly_view():
    today = date.today()
    monthly_recs = Reconciliation.query.filter_by(frequency='Monthly').order_by(Reconciliation.due_date.asc()).all()
    members = TeamMember.query.all()
    return render_template('frequency_view.html', recs=monthly_recs, members=members, today=today,
                         frequency='Monthly', title='Monthly Reconciliations')

# ============== SETTINGS ==============

@app.route('/settings')
@login_required
def settings():
    return render_template('settings.html', db_path=db_path)

# ============== INITIALIZE ==============

def init_db():
    with app.app_context():
        db.create_all()
        if User.query.count() == 0:
            admin = User(username='admin', name='Administrator', role='admin')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("\n" + "="*50)
            print("DEFAULT ADMIN ACCOUNT CREATED")
            print("="*50)
            print("Username: admin")
            print("Password: admin123")
            print("PLEASE CHANGE THIS PASSWORD AFTER FIRST LOGIN!")
            print("="*50 + "\n")

# Initialize database when app is imported (for gunicorn/production)
init_db()

if __name__ == '__main__':
    init_db()
    print("\n" + "="*50)
    print("Reconciliation App is running!")
    print("Open your browser and go to: http://127.0.0.1:5000")
    print("="*50)
    print(f"\nDATA STORED AT: {db_path}\n")
    app.run(debug=False, host='127.0.0.1', port=5000)
