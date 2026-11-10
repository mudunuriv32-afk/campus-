from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from app.extensions import db
from app.models.item import Item
from app.models.claim import Claim
from app.models.notification import Notification
from app.models.audit import AuditLog
from app.services.auth_service import get_current_user, login_required, roles_accepted
from app.services.upload_service import validate_and_save_image
from app.forms.profile_forms import ProfilePhotoUploadForm, ProfileEditForm

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/dashboard')
@dashboard_bp.route('/dashboard/student')
@login_required
def student_dashboard():
    user = get_current_user()

    # Dashboard Metrics
    my_reports_count = Item.query.filter_by(reporter_id=user.id).count()
    my_lost_count = Item.query.filter_by(reporter_id=user.id, item_type='LOST').count()
    my_found_count = Item.query.filter_by(reporter_id=user.id, item_type='FOUND').count()
    my_active_claims = Claim.query.filter_by(claimant_id=user.id, status='PENDING').count()
    my_approved_claims = Claim.query.filter_by(claimant_id=user.id, status='APPROVED').count()
    my_returned_items = Item.query.filter_by(reporter_id=user.id, status='RETURNED').count()

    # Recent reports submitted by user
    recent_reports = Item.query.filter_by(reporter_id=user.id)\
        .order_by(Item.created_at.desc()).limit(5).all()

    # Claims on items reported by user awaiting review
    claims_needing_review = Claim.query.join(Item).filter(
        Item.reporter_id == user.id,
        Claim.status == 'PENDING'
    ).order_by(Claim.created_at.desc()).all()

    # Recent notifications
    recent_notifications = Notification.query.filter_by(user_id=user.id)\
        .order_by(Notification.created_at.desc()).limit(5).all()

    stats = {
        'total_reports': my_reports_count,
        'lost_items': my_lost_count,
        'found_items': my_found_count,
        'active_claims': my_active_claims,
        'approved_claims': my_approved_claims,
        'returned_items': my_returned_items
    }

    return render_template('dashboard/student_dashboard.html',
                           user=user,
                           stats=stats,
                           recent_reports=recent_reports,
                           claims_needing_review=claims_needing_review,
                           recent_notifications=recent_notifications)


@dashboard_bp.route('/staff/dashboard')
@roles_accepted('staff', 'admin')
def staff_dashboard():
    user = get_current_user()

    # Campus-wide operational metrics for staff
    total_open_items = Item.query.filter_by(status='OPEN').count()
    total_flagged_items = Item.query.filter_by(status='FLAGGED').count()
    total_pending_claims = Claim.query.filter_by(status='PENDING').count()
    total_returned_items = Item.query.filter_by(status='RETURNED').count()

    flagged_items = Item.query.filter_by(status='FLAGGED')\
        .order_by(Item.updated_at.desc()).limit(10).all()

    recent_claims = Claim.query.filter_by(status='PENDING')\
        .order_by(Claim.created_at.desc()).limit(10).all()

    stats = {
        'open_items': total_open_items,
        'flagged_items': total_flagged_items,
        'pending_claims': total_pending_claims,
        'returned_items': total_returned_items
    }

    return render_template('dashboard/staff_dashboard.html',
                           user=user,
                           stats=stats,
                           flagged_items=flagged_items,
                           recent_claims=recent_claims)


@dashboard_bp.route('/notifications')
@login_required
def notifications():
    user = get_current_user()
    page = request.args.get('page', 1, type=int)

    pagination = Notification.query.filter_by(user_id=user.id)\
        .order_by(Notification.created_at.desc()).paginate(page=page, per_page=15, error_out=False)

    return render_template('dashboard/notifications.html',
                           notifications=pagination.items,
                           pagination=pagination)


@dashboard_bp.route('/notifications/<int:notif_id>/read', methods=['POST'])
@login_required
def mark_notification_read(notif_id):
    user = get_current_user()
    notif = Notification.query.filter_by(id=notif_id, user_id=user.id).first_or_404()
    notif.is_read = True
    db.session.commit()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True})

    if notif.link_url:
        return redirect(notif.link_url)
    return redirect(url_for('dashboard.notifications'))


@dashboard_bp.route('/notifications/read-all', methods=['POST'])
@login_required
def mark_all_notifications_read():
    user = get_current_user()
    Notification.query.filter_by(user_id=user.id, is_read=False).update({'is_read': True})
    db.session.commit()

    flash("All notifications marked as read.", "info")
    return redirect(url_for('dashboard.notifications'))


@dashboard_bp.route('/profile', methods=['GET', 'POST'])
@dashboard_bp.route('/dashboard/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """Student / User profile view with photo upload and immutable College ID."""
    user = get_current_user()
    photo_form = ProfilePhotoUploadForm()
    edit_form = ProfileEditForm(phone=user.phone)

    if request.method == 'POST':
        if 'photo' in request.files and photo_form.validate_on_submit():
            file = photo_form.photo.data
            if file and file.filename:
                success, result = validate_and_save_image(file, subfolder='profiles')
                if success:
                    user.profile_photo = f"profiles/{result}"
                    db.session.commit()
                    flash("Profile photo updated successfully!", "success")
                    return redirect(url_for('dashboard.profile'))
                else:
                    flash(f"Photo upload error: {result}", "danger")
        elif 'phone' in request.form and edit_form.validate_on_submit():
            user.phone = edit_form.phone.data.strip()
            db.session.commit()
            flash("Contact phone number updated successfully!", "success")
            return redirect(url_for('dashboard.profile'))

    reports_count = Item.query.filter_by(reporter_id=user.id).count()
    claims_count = Claim.query.filter_by(claimant_id=user.id).count()

    return render_template('dashboard/profile.html',
                           user=user,
                           photo_form=photo_form,
                           edit_form=edit_form,
                           reports_count=reports_count,
                           claims_count=claims_count)
