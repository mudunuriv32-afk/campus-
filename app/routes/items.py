import os
from datetime import datetime, timezone
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, current_app
from app.extensions import db
from app.models.item import Item, ItemCategory, ItemImage
from app.models.audit import AuditLog
from app.forms.item_forms import ItemReportForm, ItemSearchForm, FlagReportForm
from app.services.auth_service import get_current_user, login_required
from app.services.upload_service import validate_and_save_image
from app.services.item_service import search_items, find_matching_suggestions
from app.services.notification_service import broadcast_lost_item_to_students
from app.services.cache_service import cache
from app.services.bot_detection_service import check_honeypot, log_bot_activity

items_bp = Blueprint('items', __name__, url_prefix='/items')


@items_bp.route('/lost')
def lost_items():
    form = ItemSearchForm(request.args)
    categories = ItemCategory.query.order_by(ItemCategory.name).all()
    form.category_id.choices = [('', 'All Categories')] + [(str(c.id), c.name) for c in categories]

    page = request.args.get('page', 1, type=int)
    keyword = request.args.get('keyword')
    category_id = request.args.get('category_id')
    location = request.args.get('location')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')

    pagination = search_items(
        item_type='LOST',
        keyword=keyword,
        category_id=category_id,
        location=location,
        date_from=date_from,
        date_to=date_to,
        status='OPEN',
        page=page,
        per_page=9
    )

    return render_template('items/lost_items.html',
                           items=pagination.items,
                           pagination=pagination,
                           form=form,
                           active_category=category_id,
                           categories=categories)


@items_bp.route('/found')
def found_items():
    form = ItemSearchForm(request.args)
    categories = ItemCategory.query.order_by(ItemCategory.name).all()
    form.category_id.choices = [('', 'All Categories')] + [(str(c.id), c.name) for c in categories]

    page = request.args.get('page', 1, type=int)
    keyword = request.args.get('keyword')
    category_id = request.args.get('category_id')
    location = request.args.get('location')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')

    pagination = search_items(
        item_type='FOUND',
        keyword=keyword,
        category_id=category_id,
        location=location,
        date_from=date_from,
        date_to=date_to,
        status='OPEN',
        page=page,
        per_page=9
    )

    return render_template('items/found_items.html',
                           items=pagination.items,
                           pagination=pagination,
                           form=form,
                           active_category=category_id,
                           categories=categories)


@items_bp.route('/report-lost', methods=['GET', 'POST'])
@login_required
def report_lost():
    user = get_current_user()
    if request.method == 'POST' and check_honeypot(request):
        log_bot_activity(request, "Honeypot triggered on report_lost", user.id)
        abort(400)

    form = ItemReportForm()
    categories = ItemCategory.query.order_by(ItemCategory.name).all()
    form.category_id.choices = [(c.id, c.name) for c in categories]

    if form.validate_on_submit():
        item = Item(
            title=form.title.data.strip(),
            item_type='LOST',
            category_id=form.category_id.data,
            description=form.description.data.strip(),
            identifying_features=form.identifying_features.data.strip() if form.identifying_features.data else None,
            location=form.location.data.strip(),
            incident_date=form.incident_date.data,
            incident_time=form.incident_time.data,
            contact_preference=form.contact_preference.data,
            status='OPEN',
            reporter_id=user.id
        )
        db.session.add(item)
        db.session.flush()

        # Handle image upload if provided
        if form.image.data and form.image.data.filename:
            success, filename_or_err = validate_and_save_image(form.image.data, subfolder='items')
            if success:
                img = ItemImage(
                    item_id=item.id,
                    filename=f"items/{filename_or_err}",
                    original_name=form.image.data.filename,
                    is_primary=True
                )
                db.session.add(img)
            else:
                flash(f"Image warning: {filename_or_err}. Report was saved without image.", "warning")

        AuditLog.log(
            action='ITEM_CREATED',
            user_id=user.id,
            target_type='Item',
            target_id=item.id,
            ip_address=request.remote_addr,
            details=f"Lost item reported: '{item.title}' in {item.location}"
        )
        db.session.commit()

        # Invalidate landing page statistics cache
        cache.invalidate_prefix('stats:')

        # Broadcast lost item notification to all active students
        broadcast_count = broadcast_lost_item_to_students(item)

        if broadcast_count > 0:
            flash(f"Lost item report published! Campus-wide broadcast alert sent to {broadcast_count} student accounts.", "success")
        else:
            flash("Lost item report successfully published!", "success")
        return redirect(url_for('items.item_details', item_id=item.id))

    return render_template('items/report_lost.html', form=form)


@items_bp.route('/report-found', methods=['GET', 'POST'])
@login_required
def report_found():
    user = get_current_user()
    if request.method == 'POST' and check_honeypot(request):
        log_bot_activity(request, "Honeypot triggered on report_found", user.id)
        abort(400)

    form = ItemReportForm()
    categories = ItemCategory.query.order_by(ItemCategory.name).all()
    form.category_id.choices = [(c.id, c.name) for c in categories]

    if form.validate_on_submit():
        item = Item(
            title=form.title.data.strip(),
            item_type='FOUND',
            category_id=form.category_id.data,
            description=form.description.data.strip(),
            identifying_features=form.identifying_features.data.strip() if form.identifying_features.data else None,
            location=form.location.data.strip(),
            incident_date=form.incident_date.data,
            incident_time=form.incident_time.data,
            contact_preference=form.contact_preference.data,
            status='OPEN',
            reporter_id=user.id
        )
        db.session.add(item)
        db.session.flush()

        if form.image.data and form.image.data.filename:
            success, filename_or_err = validate_and_save_image(form.image.data, subfolder='items')
            if success:
                img = ItemImage(
                    item_id=item.id,
                    filename=f"items/{filename_or_err}",
                    original_name=form.image.data.filename,
                    is_primary=True
                )
                db.session.add(img)
            else:
                flash(f"Image warning: {filename_or_err}. Report saved without image.", "warning")

        AuditLog.log(
            action='ITEM_CREATED',
            user_id=user.id,
            target_type='Item',
            target_id=item.id,
            ip_address=request.remote_addr,
            details=f"Found item reported: '{item.title}' in {item.location}"
        )
        db.session.commit()

        # Invalidate landing page statistics cache
        cache.invalidate_prefix('stats:')

        flash("Found item report successfully published!", "success")
        return redirect(url_for('items.item_details', item_id=item.id))

    return render_template('items/report_found.html', form=form)


@items_bp.route('/<int:item_id>')
def item_details(item_id):
    item = Item.query.get_or_404(item_id)
    user = get_current_user()
    flag_form = FlagReportForm()

    # Find matching candidates of opposite type
    matches = find_matching_suggestions(item, limit=3)

    return render_template('items/item_detail.html',
                           item=item,
                           matches=matches,
                           flag_form=flag_form,
                           current_user=user)


@items_bp.route('/<int:item_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_item(item_id):
    item = Item.query.get_or_404(item_id)
    user = get_current_user()

    # Authorization check: only reporter or admin can edit
    if item.reporter_id != user.id and not user.is_admin:
        abort(403)

    form = ItemReportForm(obj=item)
    categories = ItemCategory.query.order_by(ItemCategory.name).all()
    form.category_id.choices = [(c.id, c.name) for c in categories]

    if form.validate_on_submit():
        item.title = form.title.data.strip()
        item.category_id = form.category_id.data
        item.description = form.description.data.strip()
        item.identifying_features = form.identifying_features.data.strip() if form.identifying_features.data else None
        item.location = form.location.data.strip()
        item.incident_date = form.incident_date.data
        item.incident_time = form.incident_time.data
        item.contact_preference = form.contact_preference.data
        item.updated_at = datetime.now(timezone.utc)

        if form.image.data and form.image.data.filename:
            success, filename_or_err = validate_and_save_image(form.image.data, subfolder='items')
            if success:
                # Add new primary image
                for old in item.images:
                    old.is_primary = False
                img = ItemImage(
                    item_id=item.id,
                    filename=f"items/{filename_or_err}",
                    original_name=form.image.data.filename,
                    is_primary=True
                )
                db.session.add(img)

        AuditLog.log(
            action='ITEM_EDITED',
            user_id=user.id,
            target_type='Item',
            target_id=item.id,
            ip_address=request.remote_addr,
            details=f"Item #{item.id} edited by {user.email}"
        )
        db.session.commit()

        flash("Listing updated successfully.", "success")
        return redirect(url_for('items.item_details', item_id=item.id))

    return render_template('items/edit_item.html', form=form, item=item)


@items_bp.route('/<int:item_id>/close', methods=['POST'])
@login_required
def close_item(item_id):
    item = Item.query.get_or_404(item_id)
    user = get_current_user()

    if item.reporter_id != user.id and not user.is_admin and not user.is_staff:
        abort(403)

    item.status = 'CLOSED'
    item.updated_at = datetime.now(timezone.utc)

    AuditLog.log(
        action='ITEM_CLOSED',
        user_id=user.id,
        target_type='Item',
        target_id=item.id,
        ip_address=request.remote_addr,
        details=f"Item #{item.id} closed by {user.email}"
    )
    db.session.commit()

    flash("Item listing has been closed.", "info")
    return redirect(url_for('items.item_details', item_id=item.id))


@items_bp.route('/<int:item_id>/flag', methods=['POST'])
@login_required
def flag_item(item_id):
    item = Item.query.get_or_404(item_id)
    user = get_current_user()
    form = FlagReportForm()

    if form.validate_on_submit():
        item.status = 'FLAGGED'
        item.flagged_reason = form.reason.data.strip()

        AuditLog.log(
            action='ITEM_FLAGGED',
            user_id=user.id,
            target_type='Item',
            target_id=item.id,
            ip_address=request.remote_addr,
            details=f"Item #{item.id} flagged by {user.email}: {item.flagged_reason}"
        )
        db.session.commit()

        flash("Thank you. This listing has been flagged for campus moderation.", "info")
    return redirect(url_for('items.item_details', item_id=item.id))


@items_bp.route('/my-reports')
@login_required
def my_reports():
    user = get_current_user()
    page = request.args.get('page', 1, type=int)
    item_type = request.args.get('type')  # Optional 'LOST' or 'FOUND'

    query = Item.query.filter_by(reporter_id=user.id)
    if item_type in ('LOST', 'FOUND'):
        query = query.filter_by(item_type=item_type)

    pagination = query.order_by(Item.created_at.desc()).paginate(page=page, per_page=10, error_out=False)

    return render_template('items/my_reports.html',
                           items=pagination.items,
                           pagination=pagination,
                           active_type=item_type)
