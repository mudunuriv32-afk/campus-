import pytest
from app.extensions import db
from app.models.item import Item
from app.models.claim import Claim
from app.models.user import User
from datetime import date


def test_submit_claim_workflow(client, auth_client, app):
    """Test student submitting claim on a found item."""
    auth_client('student@campusconnect.edu', 'Student@2026!')

    with app.app_context():
        # Found item reported by staff@campusconnect.edu
        item = Item.query.filter_by(title='Found: Stainless Steel Hydro Flask (Blue)').first()
        item_id = item.id

    response = client.post(f'/claims/request/{item_id}', data={
        'claim_description': 'This is my water bottle left after gym class on Monday.',
        'verification_details': 'There is a scratch under the lid and a Yosemite sticker on the side.'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Your claim request has been sent to the reporter" in response.data

    with app.app_context():
        claim = Claim.query.filter_by(item_id=item_id).first()
        assert claim is not None
        assert claim.status == 'PENDING'
        assert b"scratch under the lid" in claim.verification_details.encode()

        item = db.session.get(Item, item_id)
        assert item.status == 'CLAIM_PENDING'


def test_duplicate_active_claim_prevented(client, auth_client, app):
    """Test that a user cannot submit a second pending claim for the same item."""
    auth_client('samantha@campusconnect.edu', 'Student@2026!')

    with app.app_context():
        found_item = Item.query.filter_by(title='Found: Stainless Steel Hydro Flask (Blue)').first()
        item_id = found_item.id

    # 1. First claim submission
    res1 = client.post(f'/claims/request/{item_id}', data={
        'claim_description': 'First claim attempt description',
        'verification_details': 'First details'
    }, follow_redirects=True)
    assert b"Your claim request has been sent to the reporter" in res1.data

    # 2. Try submitting duplicate claim
    res2 = client.post(f'/claims/request/{item_id}', data={
        'claim_description': 'Duplicate claim attempt description',
        'verification_details': 'Duplicate details'
    }, follow_redirects=True)

    assert b"already have an active pending claim" in res2.data


def test_claim_on_own_item_prohibited(client, auth_client, app):
    """Test that reporter cannot claim their own item."""
    auth_client('staff@campusconnect.edu', 'Staff@2026!')

    with app.app_context():
        item = Item.query.filter_by(title='Found: Stainless Steel Hydro Flask (Blue)').first()
        item_id = item.id

    res = client.get(f'/claims/request/{item_id}', follow_redirects=True)
    assert b"cannot claim an item you reported yourself" in res.data


def test_claim_approval_transaction(client, auth_client, app):
    """Test atomic claim approval marks item RETURNED and dispatches notification."""
    # 1. First Samantha submits a claim on the item reported by staff
    auth_client('samantha@campusconnect.edu', 'Student@2026!')
    with app.app_context():
        item = Item.query.filter_by(title='Found: Stainless Steel Hydro Flask (Blue)').first()
        item_id = item.id

    client.post(f'/claims/request/{item_id}', data={
        'claim_description': 'This is my Hydro Flask bottle.',
        'verification_details': 'Yosemite mountain sticker on side.'
    }, follow_redirects=True)

    with app.app_context():
        claim = Claim.query.filter_by(item_id=item_id, status='PENDING').first()
        assert claim is not None
        claim_id = claim.id

    # 2. Now reporter (staff) reviews and approves the claim
    auth_client('staff@campusconnect.edu', 'Staff@2026!')
    res = client.post(f'/claims/review/{claim_id}', data={
        'action': 'APPROVE',
        'remarks': 'Verification verified. Pick up at CSE Department Office 201.'
    }, follow_redirects=True)

    assert res.status_code == 200
    assert b"marked as RETURNED" in res.data

    with app.app_context():
        updated_claim = db.session.get(Claim, claim_id)
        assert updated_claim.status == 'APPROVED'
        assert updated_claim.reviewed_at is not None

        updated_item = db.session.get(Item, item_id)
        assert updated_item.status == 'RETURNED'


def test_unauthorized_claim_review_forbidden(client, auth_client, app):
    """Test that an unrelated student cannot review/approve another user's claim."""
    # 1. Samantha submits a claim on item reported by staff
    auth_client('samantha@campusconnect.edu', 'Student@2026!')
    with app.app_context():
        item = Item.query.filter_by(title='Found: Stainless Steel Hydro Flask (Blue)').first()
        item_id = item.id

    client.post(f'/claims/request/{item_id}', data={
        'claim_description': 'Claim to test unauth review.',
        'verification_details': 'Verification details.'
    }, follow_redirects=True)

    with app.app_context():
        claim = Claim.query.filter_by(item_id=item_id, status='PENDING').first()
        claim_id = claim.id

    # 2. Unrelated student Jordan tries to access review page
    auth_client('student@campusconnect.edu', 'Student@2026!')
    res = client.get(f'/claims/review/{claim_id}')
    assert res.status_code == 403


def test_claimant_cancel_own_claim(client, auth_client, app):
    """Test claimant cancelling their own pending claim."""
    with app.app_context():
        reporter = User.query.filter_by(email='admin@campusconnect.edu').first()
        claimant = User.query.filter_by(email='student@campusconnect.edu').first()
        claimant_id = claimant.id
        item = Item(
            title='Test Umbrella for Cancellation',
            item_type='FOUND',
            category_id=1,
            location='Campus Library Entrance',
            incident_date=date.today(),
            description='Black folding umbrella found near door.',
            status='OPEN',
            reporter_id=reporter.id
        )
        db.session.add(item)
        db.session.commit()
        item_id = item.id

    auth_client('student@campusconnect.edu', 'Student@2026!')
    client.post(f'/claims/request/{item_id}', data={
        'claim_description': 'My black umbrella left yesterday.',
        'verification_details': 'Has wooden curved handle.'
    }, follow_redirects=True)

    with app.app_context():
        c = Claim.query.filter_by(item_id=item_id, claimant_id=claimant_id).first()
        assert c is not None
        c_id = c.id

    res_cancel = client.post(f'/claims/{c_id}/cancel', follow_redirects=True)
    assert res_cancel.status_code == 200
    assert b"claim has been cancelled" in res_cancel.data

    with app.app_context():
        updated_c = db.session.get(Claim, c_id)
        assert updated_c.status == 'CANCELLED'
