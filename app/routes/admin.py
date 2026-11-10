from datetime import datetime, timezone, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, session
from app.extensions import db
from app.models.user import User, Role, Department
from app.models.item import Item, ItemCategory
from app.models.claim import Claim
from app.models.audit import AuditLog
from app.models.settings import PlatformSetting
from app.models.password_reset import PasswordResetRecord
from app.forms.admin_forms import CollegeIdSearchForm, ConfirmResetForm
from app.services.auth_service import get_current_user, roles_accepted
from app.services.claim_service import approve_claim, reject_claim
from app.services.notification_service import send_notification
from app.services.password_reset_service import (
    search_user_by_campus_id,
    initiate_admin_password_reset,
    get_reset_history
)

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.before_request
@roles_accepted('admin')
def require_admin_role():
    """Enforce strict backend administrator authentication for all routes in this blueprint."""
    pass


@admin_bp.route('/dashboard')
def dashboard():
    # Platform Analytics
    total_users = User.query.count()
    student_role = Role.query.filter_by(name='student').first()
    staff_role = Role.query.filter_by(name='staff').first()
    
    total_students = User.query.filter_by(role_id=student_role.id).count() if student_role else 0
    total_staff = User.query.filter_by(role_id=staff_role.id).count() if staff_role else 0
    pending_staff_approvals = User.query.filter_by(is_approved=False).count()

    total_lost = Item.query.filter_by(item_type='LOST').count()
    total_found = Item.query.filter_by(item_type='FOUND').count()
    pending_claims = Claim.query.filter_by(status='PENDING').count()
    returned_items = Item.query.filter_by(status='RETURNED').count()
    flagged_reports = Item.query.filter_by(status='FLAGGED').count()

    # Recent Audit Logs
    recent_logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(8).all()

    stats = {
        'total_users': total_users,
        'total_students': total_students,
        'total_staff': total_staff,
        'pending_staff_approvals': pending_staff_approvals,
        'total_lost': total_lost,
        'total_found': total_found,
        'pending_claims': pending_claims,
        'returned_items': returned_items,
        'flagged_reports': flagged_reports
    }

    # Chart.js analytics metrics
    all_cats = ItemCategory.query.order_by(ItemCategory.name).all()
    cat_labels = [c.name for c in all_cats]
    cat_counts = [Item.query.filter_by(category_id=c.id).count() for c in all_cats]

    status_chart = {
        'labels': ['Lost Reports', 'Found Published', 'Pending Claims', 'Returned Belongings'],
        'data': [total_lost, total_found, pending_claims, returned_items]
    }
    category_chart = {
        'labels': cat_labels,
        'data': cat_counts
    }

    return render_template(
        'admin/admin_dashboard.html',
        stats=stats,
        recent_logs=recent_logs,
        status_chart=status_chart,
        category_chart=category_chart
    )


@admin_bp.route('/users')
def users():
    search = request.args.get('q', '').strip()
    role_filter = request.args.get('role', '')
    status_filter = request.args.get('status', '')
    page = request.args.get('page', 1, type=int)

    query = User.query

    if search:
        kw = f"%{search}%"
        query = query.filter(
            (User.full_name.ilike(kw)) |
            (User.email.ilike(kw)) |
            (User.campus_id.ilike(kw))
        )

    if role_filter:
        query = query.join(Role).filter(Role.name == role_filter)

    if status_filter == 'active':
        query = query.filter(User.is_active == True)
    elif status_filter == 'inactive':
        query = query.filter(User.is_active == False)
    elif status_filter == 'pending_approval':
        query = query.filter(User.is_approved == False)

    pagination = query.order_by(User.created_at.desc()).paginate(page=page, per_page=15, error_out=False)
    roles = Role.query.all()

    return render_template('admin/user_management.html',
                           users=pagination.items,
                           pagination=pagination,
                           roles=roles,
                           search=search,
                           role_filter=role_filter,
                           status_filter=status_filter)


@admin_bp.route('/users/<int:user_id>/toggle-status', methods=['POST'])
def toggle_user_status(user_id):
    current_admin = get_current_user()
    user = User.query.get_or_404(user_id)

    if user.id == current_admin.id:
        flash("You cannot deactivate your own administrative account.", "danger")
        return redirect(url_for('admin.users'))

    user.is_active = not user.is_active
    action_name = 'USER_ACTIVATED' if user.is_active else 'USER_DEACTIVATED'

    AuditLog.log(
        action=action_name,
        user_id=current_admin.id,
        target_type='User',
        target_id=user.id,
        ip_address=request.remote_addr,
        details=f"Admin {current_admin.email} toggled status of {user.email} to active={user.is_active}"
    )
    db.session.commit()

    flash(f"User {user.email} is now {'activated' if user.is_active else 'deactivated'}.", "success")
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<int:user_id>/approve-staff', methods=['POST'])
def approve_staff(user_id):
    current_admin = get_current_user()
    user = User.query.get_or_404(user_id)

    user.is_approved = True
    AuditLog.log(
        action='STAFF_APPROVED',
        user_id=current_admin.id,
        target_type='User',
        target_id=user.id,
        ip_address=request.remote_addr,
        details=f"Admin {current_admin.email} verified and approved staff user {user.email}"
    )

    send_notification(
        user_id=user.id,
        title="Staff Account Approved",
        message="Your official staff account has been approved by the campus administration. You now have full staff portal access.",
        link_url="/staff/dashboard",
        notification_type="SYSTEM_ANNOUNCEMENT"
    )

    db.session.commit()
    flash(f"Staff account for {user.full_name} ({user.email}) approved successfully.", "success")
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<int:user_id>/change-role', methods=['POST'])
def change_user_role(user_id):
    current_admin = get_current_user()
    user = User.query.get_or_404(user_id)
    new_role_id = request.form.get('role_id', type=int)

    if not new_role_id:
        flash("Invalid role selection.", "danger")
        return redirect(url_for('admin.users'))

    new_role = Role.query.get_or_404(new_role_id)
    old_role_name = user.role.name if user.role else 'None'
    user.role_id = new_role.id

    AuditLog.log(
        action='ROLE_CHANGED',
        user_id=current_admin.id,
        target_type='User',
        target_id=user.id,
        ip_address=request.remote_addr,
        details=f"Admin {current_admin.email} changed role of {user.email} from {old_role_name} to {new_role.name}"
    )
    db.session.commit()

    flash(f"Role updated to '{new_role.name}' for {user.email}.", "success")
    return redirect(url_for('admin.users'))


@admin_bp.route('/items')
def items():
    search = request.args.get('q', '').strip()
    status_filter = request.args.get('status', '')
    type_filter = request.args.get('type', '')
    page = request.args.get('page', 1, type=int)

    query = Item.query

    if search:
        kw = f"%{search}%"
        query = query.filter((Item.title.ilike(kw)) | (Item.location.ilike(kw)))

    if status_filter:
        query = query.filter(Item.status == status_filter)

    if type_filter in ('LOST', 'FOUND'):
        query = query.filter(Item.item_type == type_filter)

    pagination = query.order_by(Item.created_at.desc()).paginate(page=page, per_page=15, error_out=False)

    return render_template('admin/item_management.html',
                           items=pagination.items,
                           pagination=pagination,
                           search=search,
                           status_filter=status_filter,
                           type_filter=type_filter)


@admin_bp.route('/items/<int:item_id>/moderate', methods=['POST'])
def moderate_item(item_id):
    current_admin = get_current_user()
    item = Item.query.get_or_404(item_id)
    action = request.form.get('action')  # 'UNFLAG', 'CLOSE', 'DELETE'

    if action == 'UNFLAG':
        item.status = 'OPEN'
        item.flagged_reason = None
        flash("Item unflagged and restored to OPEN status.", "success")
    elif action == 'CLOSE':
        item.status = 'CLOSED'
        flash("Item listing has been closed.", "info")
    elif action == 'DELETE':
        db.session.delete(item)
        flash("Item permanently removed.", "warning")

    AuditLog.log(
        action=f"ITEM_MODERATED_{action}",
        user_id=current_admin.id,
        target_type='Item',
        target_id=item_id,
        ip_address=request.remote_addr,
        details=f"Admin {current_admin.email} moderated item #{item_id} with action {action}"
    )
    db.session.commit()
    return redirect(url_for('admin.items'))


@admin_bp.route('/claims')
def claims():
    status_filter = request.args.get('status', '')
    page = request.args.get('page', 1, type=int)

    query = Claim.query
    if status_filter:
        query = query.filter(Claim.status == status_filter)

    pagination = query.order_by(Claim.created_at.desc()).paginate(page=page, per_page=15, error_out=False)

    return render_template('admin/claim_management.html',
                           claims=pagination.items,
                           pagination=pagination,
                           status_filter=status_filter)


@admin_bp.route('/claims/<int:claim_id>/resolve', methods=['POST'])
def resolve_claim(claim_id):
    current_admin = get_current_user()
    action = request.form.get('action')  # 'APPROVE' or 'REJECT'
    remarks = request.form.get('remarks', 'Administrative resolution')

    if action == 'APPROVE':
        success, msg = approve_claim(
            claim_id=claim_id,
            reviewer_id=current_admin.id,
            remarks=f"[Admin Action] {remarks}",
            ip_address=request.remote_addr
        )
    else:
        success, msg = reject_claim(
            claim_id=claim_id,
            reviewer_id=current_admin.id,
            remarks=f"[Admin Action] {remarks}",
            ip_address=request.remote_addr
        )

    flash(msg, "success" if success else "danger")
    return redirect(url_for('admin.claims'))


@admin_bp.route('/categories', methods=['GET', 'POST'])
def categories():
    current_admin = get_current_user()
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        icon = request.form.get('icon', 'bi-tag').strip()
        description = request.form.get('description', '').strip()

        if not name:
            flash("Category name is required.", "danger")
        else:
            existing = ItemCategory.query.filter_by(name=name).first()
            if existing:
                flash("Category already exists.", "warning")
            else:
                cat = ItemCategory(name=name, icon=icon, description=description)
                db.session.add(cat)
                AuditLog.log(
                    action='CATEGORY_CREATED',
                    user_id=current_admin.id,
                    target_type='Category',
                    ip_address=request.remote_addr,
                    details=f"Admin created category '{name}'"
                )
                db.session.commit()
                flash(f"Category '{name}' created successfully.", "success")
                return redirect(url_for('admin.categories'))

    categories_list = ItemCategory.query.order_by(ItemCategory.name).all()
    return render_template('admin/categories.html', categories=categories_list)


@admin_bp.route('/audit-logs')
def audit_logs():
    action_filter = request.args.get('action', '')
    page = request.args.get('page', 1, type=int)

    query = AuditLog.query
    if action_filter:
        query = query.filter(AuditLog.action.ilike(f"%{action_filter}%"))

    pagination = query.order_by(AuditLog.created_at.desc()).paginate(page=page, per_page=20, error_out=False)

    return render_template('admin/audit_logs.html',
                           logs=pagination.items,
                           pagination=pagination,
                           action_filter=action_filter)


@admin_bp.route('/settings', methods=['GET', 'POST'])
def settings():
    current_admin = get_current_user()

    if request.method == 'POST':
        for key in request.form:
            if key != 'csrf_token':
                PlatformSetting.set(key, request.form[key].strip())

        AuditLog.log(
            action='SETTINGS_UPDATED',
            user_id=current_admin.id,
            target_type='Setting',
            ip_address=request.remote_addr,
            details=f"Admin {current_admin.email} updated platform settings."
        )
        db.session.commit()
        flash("Platform configuration saved successfully.", "success")
        return redirect(url_for('admin.settings'))

    settings_dict = {s.key: s.value for s in PlatformSetting.query.all()}
    return render_template('admin/settings.html', settings=settings_dict)


@admin_bp.route('/password-reset', methods=['GET'])
def password_reset():
    """Admin Password Reset Portal with College ID lookup, one-time temp password generation, and history."""
    search_query = request.args.get('college_id', '').strip()
    page = request.args.get('page', 1, type=int)

    target_user = None
    if search_query:
        target_user = search_user_by_campus_id(search_query)
        if not target_user:
            flash(f"No user account found matching College ID / User ID '{search_query}'.", "warning")

    reset_history = get_reset_history(page=page, per_page=10)
    confirm_form = ConfirmResetForm()
    search_form = CollegeIdSearchForm(college_id=search_query)

    # Check if a temporary password was just generated in session to reveal once
    revealed_info = session.pop('revealed_temp_password', None)

    return render_template('admin/password_reset.html',
                           target_user=target_user,
                           search_query=search_query,
                           reset_history=reset_history,
                           confirm_form=confirm_form,
                           search_form=search_form,
                           revealed_info=revealed_info)


@admin_bp.route('/password-reset/generate', methods=['POST'])
def generate_temporary_password():
    """Generate cryptographically secure temporary password, set 15m expiry, and force password change."""
    current_admin = get_current_user()
    target_id = request.form.get('user_id', type=int)
    if not target_id:
        flash("Invalid reset confirmation request.", "danger")
        return redirect(url_for('admin.password_reset'))

    target_user = db.session.get(User, target_id)
    if not target_user:
        flash("Target user does not exist.", "danger")
        return redirect(url_for('admin.password_reset'))

    success, msg, temp_pw = initiate_admin_password_reset(
        admin_user=current_admin,
        target_user=target_user,
        expires_in_minutes=15
    )

    if success:
        session['revealed_temp_password'] = {
            'user_name': target_user.full_name,
            'campus_id': target_user.campus_id,
            'email': target_user.email,
            'password': temp_pw,
            'expires_at': (datetime.now(timezone.utc) + timedelta(minutes=15)).strftime('%I:%M %p UTC')
        }
        flash(msg, "success")
        return redirect(url_for('admin.password_reset', college_id=target_user.campus_id))
    else:
        flash(msg, "danger")
        return redirect(url_for('admin.password_reset', college_id=target_user.campus_id))


@admin_bp.route('/students', methods=['GET'])
def students():
    """Dedicated Student Management section with College ID lookup."""
    search_query = request.args.get('college_id', '').strip()
    searched_student = None
    student_reports = []
    student_claims = []

    if search_query:
        searched_student = search_user_by_campus_id(search_query)
        if not searched_student:
            flash(f"No student found with College ID '{search_query}'.", "warning")
        else:
            student_reports = searched_student.reported_items.order_by(Item.created_at.desc()).limit(10).all()
            student_claims = searched_student.claims.order_by(Claim.created_at.desc()).limit(10).all()

    student_role = Role.query.filter_by(name='student').first()
    all_students = []
    if student_role:
        all_students = User.query.filter_by(role_id=student_role.id).order_by(User.created_at.desc()).limit(15).all()

    return render_template('admin/student_search.html',
                           search_query=search_query,
                           searched_student=searched_student,
                           student_reports=student_reports,
                           student_claims=student_claims,
                           all_students=all_students)
