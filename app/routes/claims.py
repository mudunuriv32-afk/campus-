from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from app.extensions import db
from app.models.item import Item
from app.models.claim import Claim
from app.models.audit import AuditLog
from app.forms.claim_forms import ClaimSubmitForm, ClaimReviewForm
from app.services.auth_service import get_current_user, login_required
from app.services.upload_service import validate_and_save_image
from app.services.claim_service import submit_claim, approve_claim, reject_claim

claims_bp = Blueprint('claims', __name__, url_prefix='/claims')


@claims_bp.route('/request/<int:item_id>', methods=['GET', 'POST'])
@login_required
def request_claim(item_id):
    item = Item.query.get_or_404(item_id)
    user = get_current_user()

    # Rule checks
    if item.reporter_id == user.id:
        flash("You cannot claim an item you reported yourself.", "warning")
        return redirect(url_for('items.item_details', item_id=item.id))

    if item.status in ('RETURNED', 'CLOSED'):
        flash(f"This item is already {item.status.lower()} and no longer accepting claims.", "warning")
        return redirect(url_for('items.item_details', item_id=item.id))

    # Check for existing pending claim
    existing_claim = Claim.query.filter_by(
        item_id=item.id,
        claimant_id=user.id,
        status='PENDING'
    ).first()
    if existing_claim:
        flash("You already have an active pending claim for this item.", "info")
        return redirect(url_for('claims.my_claims'))

    form = ClaimSubmitForm()
    if form.validate_on_submit():
        proof_filename = None
        if form.proof_image.data and form.proof_image.data.filename:
            success, filename_or_err = validate_and_save_image(form.proof_image.data, subfolder='claims')
            if success:
                proof_filename = f"claims/{filename_or_err}"
            else:
                flash(f"Proof file warning: {filename_or_err}. Claim submitted without image.", "warning")

        success, msg, claim = submit_claim(
            item_id=item.id,
            claimant_id=user.id,
            claim_description=form.claim_description.data,
            verification_details=form.verification_details.data,
            proof_image=proof_filename
        )

        if success:
            AuditLog.log(
                action='CLAIM_SUBMITTED',
                user_id=user.id,
                target_type='Claim',
                target_id=claim.id,
                ip_address=request.remote_addr,
                details=f"Claim submitted by {user.email} for item #{item.id} ('{item.title}')"
            )
            db.session.commit()
            flash("Your claim request has been sent to the reporter. You will receive a notification when reviewed.", "success")
            return redirect(url_for('claims.my_claims'))
        else:
            flash(msg, "danger")

    return render_template('claims/request_claim.html', form=form, item=item)


@claims_bp.route('/my-claims')
@login_required
def my_claims():
    user = get_current_user()
    claims = Claim.query.filter_by(claimant_id=user.id).order_by(Claim.created_at.desc()).all()
    return render_template('claims/my_claims.html', claims=claims)


@claims_bp.route('/review/<int:claim_id>', methods=['GET', 'POST'])
@login_required
def review_claim(claim_id):
    claim = Claim.query.get_or_404(claim_id)
    user = get_current_user()
    item = claim.item

    # Authorization: only the item reporter or staff/admin can review
    if item.reporter_id != user.id and not user.is_admin and not user.is_staff:
        abort(403)

    form = ClaimReviewForm()

    if form.validate_on_submit():
        action = form.action.data
        remarks = form.remarks.data.strip()
        client_ip = request.remote_addr

        if action == 'APPROVE':
            success, msg = approve_claim(
                claim_id=claim.id,
                reviewer_id=user.id,
                remarks=remarks,
                ip_address=client_ip
            )
            if success:
                flash(msg, "success")
                return redirect(url_for('items.item_details', item_id=item.id))
            else:
                flash(msg, "danger")
        elif action == 'REJECT':
            success, msg = reject_claim(
                claim_id=claim.id,
                reviewer_id=user.id,
                remarks=remarks,
                ip_address=client_ip
            )
            if success:
                flash("Claim was rejected.", "info")
                return redirect(url_for('items.item_details', item_id=item.id))
            else:
                flash(msg, "danger")

    return render_template('claims/review_claim.html', claim=claim, item=item, form=form)


@claims_bp.route('/<int:claim_id>/cancel', methods=['POST'])
@login_required
def cancel_claim(claim_id):
    claim = Claim.query.get_or_404(claim_id)
    user = get_current_user()

    if claim.claimant_id != user.id and not user.is_admin:
        abort(403)

    if claim.status != 'PENDING':
        flash(f"Only pending claims can be cancelled.", "warning")
        return redirect(url_for('claims.my_claims'))

    claim.status = 'CANCELLED'

    # Check if item should revert to OPEN
    item = claim.item
    pending_count = Claim.query.filter(
        Claim.item_id == item.id,
        Claim.id != claim.id,
        Claim.status == 'PENDING'
    ).count()
    if pending_count == 0 and item.status == 'CLAIM_PENDING':
        item.status = 'OPEN'

    AuditLog.log(
        action='CLAIM_CANCELLED',
        user_id=user.id,
        target_type='Claim',
        target_id=claim.id,
        ip_address=request.remote_addr,
        details=f"Claim #{claim.id} cancelled by claimant {user.email}"
    )
    db.session.commit()

    flash("Your claim has been cancelled.", "info")
    return redirect(url_for('claims.my_claims'))
