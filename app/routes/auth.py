from flask import Blueprint, render_template, redirect, url_for, flash, request, session, abort, g
from sqlalchemy import func
from app.extensions import db
from app.models.user import User, Role, Department
from app.models.audit import AuditLog
from app.forms.auth_forms import (
    LoginForm,
    StudentRegisterForm,
    StaffRegisterForm,
    ChangePasswordForm,
    ForgotPasswordForm,
    ChangeTemporaryPasswordForm
)
from app.services.auth_service import (
    validate_password_strength,
    check_rate_limit,
    get_current_user,
    login_required
)
from app.services.password_reset_service import complete_temporary_password_change
from app.services.bot_detection_service import check_honeypot, log_bot_activity

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET' and get_current_user():
        return redirect(url_for('dashboard.student_dashboard'))

    if request.method == 'POST' and check_honeypot(request):
        log_bot_activity(request, "Honeypot triggered on login")
        abort(400)

    form = LoginForm()
    client_ip = request.remote_addr or '127.0.0.1'

    if form.validate_on_submit():
        # Check brute force rate limit (5 attempts / min)
        if not check_rate_limit(f"login:{client_ip}", limit=5, window_seconds=60):
            flash("Too many failed attempts. Please wait 1 minute before trying again.", "danger")
            return render_template('auth/login.html', form=form), 429

        login_input = form.email.data.strip()
        user = User.query.filter(
            db.or_(
                func.lower(User.email) == login_input.lower(),
                func.upper(User.campus_id) == login_input.upper()
            )
        ).first()

        authenticated = False
        temp_login = False
        expired_temp = False

        if user:
            if user.force_password_change:
                valid_temp, temp_msg = user.verify_temp_password(form.password.data)
                if valid_temp:
                    authenticated = True
                    temp_login = True
                elif "expired" in temp_msg.lower():
                    expired_temp = True
            else:
                if user.check_password(form.password.data):
                    authenticated = True

        if authenticated:
            if not user.is_active:
                flash("Your account has been deactivated by an administrator. Please contact campus security.", "danger")
                return render_template('auth/login.html', form=form)

            if not user.is_approved:
                flash("Your staff account is pending administrative verification. You will be notified once approved.", "warning")
                return render_template('auth/login.html', form=form)

            # Establish session
            session.clear()
            session['user_id'] = user.id
            session.permanent = form.remember_me.data
            g.current_user = user
            g._current_user_id = user.id

            AuditLog.log(
                action='USER_LOGIN_TEMP' if temp_login else 'USER_LOGIN',
                user_id=user.id,
                target_type='User',
                target_id=user.id,
                ip_address=client_ip,
                details=f"User {user.campus_id} ({user.email}) logged in {'with temporary password' if temp_login else 'successfully'}."
            )
            db.session.commit()

            if temp_login:
                flash("You have signed in using a temporary password. You must set a permanent password to continue.", "warning")
                return redirect(url_for('change_temporary_password_root'))

            flash(f"Welcome back, {user.full_name}!", "success")
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)

            if user.is_admin:
                return redirect(url_for('admin.dashboard'))
            elif user.is_staff:
                return redirect(url_for('dashboard.staff_dashboard'))
            else:
                return redirect(url_for('dashboard.student_dashboard'))
        else:
            AuditLog.log(
                action='FAILED_LOGIN',
                user_id=user.id if user else None,
                target_type='User',
                ip_address=client_ip,
                details=f"Failed login attempt for identifier {form.email.data}"
            )
            db.session.commit()
            if expired_temp:
                flash("Your temporary password has expired (valid for 15 minutes). Please contact an administrator for a new reset.", "danger")
            else:
                flash("Invalid college email or password (or College ID). Please try again.", "danger")

    return render_template('auth/login.html', form=form)


@auth_bp.route('/register-student', methods=['GET', 'POST'])
def register_student():
    if request.method == 'GET' and get_current_user():
        return redirect(url_for('dashboard.student_dashboard'))

    if request.method == 'POST' and check_honeypot(request):
        log_bot_activity(request, "Honeypot triggered on register_student")
        abort(400)

    form = StudentRegisterForm()
    # Populate department choices
    departments = Department.query.order_by(Department.name).all()
    form.department_id.choices = [(d.id, f"{d.name} ({d.code})") for d in departments]

    if form.validate_on_submit():
        # Validate password strength
        valid, err_msg = validate_password_strength(form.password.data)
        if not valid:
            flash(err_msg, "danger")
            return render_template('auth/register_student.html', form=form)

        student_role = Role.query.filter_by(name='student').first()
        if not student_role:
            flash("System configuration error: Role not initialized.", "danger")
            return render_template('auth/register_student.html', form=form)

        user = User(
            full_name=form.full_name.data.strip(),
            email=form.email.data.lower().strip(),
            campus_id=form.campus_id.data.strip().upper(),
            department_id=form.department_id.data,
            designation_or_year=form.designation_or_year.data,
            phone=form.phone.data.strip(),
            role_id=student_role.id,
            is_active=True,
            is_approved=True
        )
        user.set_password(form.password.data)

        db.session.add(user)
        db.session.flush()

        AuditLog.log(
            action='USER_REGISTER',
            user_id=user.id,
            target_type='User',
            target_id=user.id,
            ip_address=request.remote_addr,
            details=f"Student registered: {user.full_name} ({user.campus_id})"
        )
        db.session.commit()

        flash("Registration successful! You may now sign in with your college email.", "success")
        return redirect(url_for('auth.login'))

    return render_template('auth/register_student.html', form=form)


@auth_bp.route('/register-staff', methods=['GET', 'POST'])
def register_staff():
    if get_current_user():
        return redirect(url_for('dashboard.staff_dashboard'))

    if request.method == 'POST' and check_honeypot(request):
        log_bot_activity(request, "Honeypot triggered on register_staff")
        abort(400)

    form = StaffRegisterForm()
    departments = Department.query.order_by(Department.name).all()
    form.department_id.choices = [(d.id, f"{d.name} ({d.code})") for d in departments]

    if form.validate_on_submit():
        valid, err_msg = validate_password_strength(form.password.data)
        if not valid:
            flash(err_msg, "danger")
            return render_template('auth/register_staff.html', form=form)

        staff_role = Role.query.filter_by(name='staff').first()
        if not staff_role:
            flash("System configuration error: Staff role not found.", "danger")
            return render_template('auth/register_staff.html', form=form)

        user = User(
            full_name=form.full_name.data.strip(),
            email=form.email.data.lower().strip(),
            campus_id=form.campus_id.data.strip().upper(),
            department_id=form.department_id.data,
            designation_or_year=form.designation_or_year.data.strip(),
            phone=form.phone.data.strip(),
            role_id=staff_role.id,
            is_active=True,
            is_approved=False  # Requires admin approval for staff role security
        )
        user.set_password(form.password.data)

        db.session.add(user)
        db.session.flush()

        AuditLog.log(
            action='STAFF_REGISTER_REQUEST',
            user_id=user.id,
            target_type='User',
            target_id=user.id,
            ip_address=request.remote_addr,
            details=f"Staff account requested: {user.full_name} ({user.campus_id})"
        )
        db.session.commit()

        flash("Staff registration submitted! For campus security, your account will be active once verified by an administrator.", "info")
        return redirect(url_for('auth.login'))

    return render_template('auth/register_staff.html', form=form)


@auth_bp.route('/logout')
def logout():
    user = get_current_user()
    if user:
        AuditLog.log(
            action='USER_LOGOUT',
            user_id=user.id,
            target_type='User',
            target_id=user.id,
            ip_address=request.remote_addr,
            details=f"User {user.email} logged out."
        )
        db.session.commit()
    session.clear()
    g.current_user = None
    g._current_user_id = None
    flash("You have been signed out safely.", "info")
    return redirect(url_for('main.index'))


@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    user = get_current_user()
    form = ChangePasswordForm()

    if form.validate_on_submit():
        if not user.check_password(form.old_password.data):
            flash("Current password is incorrect.", "danger")
            return render_template('auth/change_password.html', form=form)

        valid, err_msg = validate_password_strength(form.new_password.data)
        if not valid:
            flash(err_msg, "danger")
            return render_template('auth/change_password.html', form=form)

        user.set_password(form.new_password.data)
        AuditLog.log(
            action='PASSWORD_CHANGED',
            user_id=user.id,
            target_type='User',
            target_id=user.id,
            ip_address=request.remote_addr,
            details=f"Password updated for {user.email}"
        )
        db.session.commit()

        flash("Password successfully updated!", "success")
        return redirect(url_for('dashboard.student_dashboard'))

    return render_template('auth/change_password.html', form=form)


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        # Check rate limit
        client_ip = request.remote_addr or '127.0.0.1'
        if not check_rate_limit(f"pwd_reset:{client_ip}", limit=3, window_seconds=60):
            flash("Too many requests. Please wait a moment.", "danger")
            return render_template('auth/forgot_password.html', form=form), 429

        user = User.query.filter_by(email=form.email.data.lower().strip()).first()
        # Security best practice: don't reveal if email exists
        flash("If your college email is registered with CampusConnect, you will receive instructions on resetting your password.", "info")
        return redirect(url_for('auth.login'))

    return render_template('auth/forgot_password.html', form=form)


@auth_bp.route('/change-temporary-password', methods=['GET', 'POST'])
def change_temporary_password():
    user = get_current_user()
    if not user:
        flash("Please sign in with your temporary password first.", "warning")
        return redirect(url_for('auth.login'))

    if not user.force_password_change:
        flash("Your account does not have a pending temporary password change.", "info")
        if user.is_admin:
            return redirect(url_for('admin.dashboard'))
        elif user.is_staff:
            return redirect(url_for('dashboard.staff_dashboard'))
        return redirect(url_for('dashboard.student_dashboard'))

    form = ChangeTemporaryPasswordForm()
    if form.validate_on_submit():
        success, msg = complete_temporary_password_change(
            user,
            form.temp_password.data,
            form.new_password.data
        )
        if success:
            flash(msg, "success")
            if user.is_admin:
                return redirect(url_for('admin.dashboard'))
            elif user.is_staff:
                return redirect(url_for('dashboard.staff_dashboard'))
            return redirect(url_for('dashboard.student_dashboard'))
        else:
            flash(msg, "danger")

    return render_template('auth/change_temp_password.html', form=form, user=user)
