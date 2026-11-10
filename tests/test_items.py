import pytest
from app.models.item import Item, ItemCategory
from app.models.user import User
from datetime import date


def test_report_lost_item(client, auth_client, app, sample_image):
    """Test reporting a lost item with image attachment."""
    auth_client('student@campusconnect.edu', 'Student@2026!')

    with app.app_context():
        category = ItemCategory.query.filter_by(name='Electronics').first()

    response = client.post('/items/report-lost', data={
        'title': 'Sony WH-1000XM4 Noise Cancelling Headphones',
        'category_id': category.id,
        'location': 'Library 3rd Floor Quiet Zone',
        'incident_date': '2026-11-08',
        'incident_time': '14:30',
        'description': 'Black over-ear headphones left in study carrel 304 inside black carrying case.',
        'identifying_features': 'Small dent on left hinge, serial ending in 4421.',
        'contact_preference': 'IN_APP',
        'image': (sample_image, 'headphones.png')
    }, follow_redirects=True, content_type='multipart/form-data')

    assert response.status_code == 200
    assert b"Sony WH-1000XM4" in response.data

    with app.app_context():
        item = Item.query.filter_by(title='Sony WH-1000XM4 Noise Cancelling Headphones').first()
        assert item is not None
        assert item.item_type == 'LOST'
        assert item.status == 'OPEN'
        assert len(item.images) > 0


def test_report_found_item(client, auth_client, app):
    """Test reporting a found item."""
    auth_client('student@campusconnect.edu', 'Student@2026!')

    with app.app_context():
        category = ItemCategory.query.filter_by(name='Keys').first()

    response = client.post('/items/report-found', data={
        'title': 'Honda Motorcycle Key with Blue Tag',
        'category_id': category.id,
        'location': 'North Parking Lot near Bike Stands',
        'incident_date': '2026-11-09',
        'description': 'Found dropped near bike stands in the north lot.',
        'identifying_features': 'Key has red rubber cover on the head.',
        'contact_preference': 'IN_APP'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Honda Motorcycle Key" in response.data

    with app.app_context():
        item = Item.query.filter_by(title='Honda Motorcycle Key with Blue Tag').first()
        assert item is not None
        assert item.item_type == 'FOUND'
        assert item.status == 'OPEN'


def test_search_and_filter_items(client):
    """Test keyword and category search filtering."""
    # Keyword search
    res = client.get('/items/lost?keyword=MacBook')
    assert res.status_code == 200
    assert b"MacBook" in res.data

    # Empty filter result
    res_none = client.get('/items/lost?keyword=NonExistentSuperRareWidget123')
    assert res_none.status_code == 200
    assert b"No Lost Items Match" in res_none.data


def test_edit_item_authorized_vs_idor(client, auth_client, app):
    """Test editing own report succeeds, but another student editing gets 403 Forbidden."""
    with app.app_context():
        # Item owned by student@campusconnect.edu (Jordan)
        item = Item.query.filter_by(title='Silver Apple MacBook Air 13-inch').first()
        item_id = item.id

    # Try editing as Samantha (unauthorized student) -> IDOR defense
    auth_client('samantha@campusconnect.edu', 'Student@2026!')
    res_unauth = client.get(f'/items/{item_id}/edit')
    assert res_unauth.status_code == 403

    # Now edit as owner (Jordan)
    auth_client('student@campusconnect.edu', 'Student@2026!')
    res_auth = client.post(f'/items/{item_id}/edit', data={
        'title': 'Silver Apple MacBook Air 13-inch (Updated Location)',
        'category_id': item.category_id,
        'location': 'Main Library - 2nd Floor Study Desk 12',
        'incident_date': str(item.incident_date),
        'description': 'Updated description: Left on desk 12 with NASA sticker.',
        'contact_preference': 'IN_APP'
    }, follow_redirects=True)

    assert res_auth.status_code == 200
    assert b"Listing updated successfully" in res_auth.data


def test_close_item_listing(client, auth_client, app):
    """Test closing a report."""
    auth_client('student@campusconnect.edu', 'Student@2026!')

    with app.app_context():
        item = Item.query.filter_by(title='Navy Blue Dell Backpack with Notebooks').first()
        item_id = item.id

    res = client.post(f'/items/{item_id}/close', follow_redirects=True)
    assert res.status_code == 200

    with app.app_context():
        updated_item = Item.query.get(item_id)
        assert updated_item.status == 'CLOSED'


def test_flag_item_listing(client, auth_client, app):
    """Test flagging an inappropriate listing."""
    auth_client('samantha@campusconnect.edu', 'Student@2026!')

    with app.app_context():
        item = Item.query.filter_by(status='OPEN').first()
        item_id = item.id

    res = client.post(f'/items/{item_id}/flag', data={
        'reason': 'Listing contains inappropriate language'
    }, follow_redirects=True)

    assert res.status_code == 200
    assert b"flagged for campus moderation" in res.data

    with app.app_context():
        updated = Item.query.get(item_id)
        assert updated.status == 'FLAGGED'
        assert updated.flagged_reason == 'Listing contains inappropriate language'
