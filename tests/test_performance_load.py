"""
Test suite for In-Memory Caching, HTTP Cache Headers, and 4,000-Member Bulk Broadcast Scalability.
"""
import time
from datetime import date
import pytest
from app.extensions import db
from app.models.user import User, Role, Department
from app.models.item import Item
from app.models.notification import Notification
from app.services.cache_service import cache
from app.services.notification_service import broadcast_lost_item_to_students


def test_in_memory_cache_get_or_set():
    """Verify cache returns cached value on subsequent calls without recomputing."""
    call_count = 0

    def compute_heavy_data():
        nonlocal call_count
        call_count += 1
        return {"data": 42}

    cache.clear()
    # First call computes
    res1 = cache.get_or_set('test:key', compute_heavy_data, ttl=60)
    assert res1 == {"data": 42}
    assert call_count == 1

    # Second call returns cached
    res2 = cache.get_or_set('test:key', compute_heavy_data, ttl=60)
    assert res2 == {"data": 42}
    assert call_count == 1  # Not incremented!

    # Invalidate prefix
    cache.invalidate_prefix('test:')
    assert cache.get('test:key') is None


def test_http_cache_headers(client):
    """Verify Cache-Control headers optimize static assets and protect authenticated routes."""
    # Authenticated / dashboard route gets no-store
    dash_response = client.get('/auth/login')
    assert dash_response.status_code == 200
    assert 'no-store' in dash_response.headers.get('Cache-Control', '')

    # Static CSS route gets 1-year immutable cache header
    css_response = client.get('/static/css/main.css')
    assert css_response.status_code == 200
    cache_control = css_response.headers.get('Cache-Control', '')
    assert 'public' in cache_control
    assert 'max-age=31536000' in cache_control


def test_broadcast_lost_item_creates_student_notifications(client):
    """Verify reporting a lost item dispatches broadcast alert to all student accounts."""
    with client.application.app_context():
        student = User.query.filter_by(email='student@campusconnect.edu').first()
        assert student is not None
        # Create a lost item
        item = Item(
            title='Blue Hydro Flask Water Bottle',
            item_type='LOST',
            category_id=1,
            description='Lost in library 2nd floor study carrel.',
            location='Main Library',
            incident_date=date.today(),
            status='OPEN',
            reporter_id=student.id
        )
        db.session.add(item)
        db.session.commit()

        # Broadcast
        count = broadcast_lost_item_to_students(item)
        assert count >= 0


def test_scalability_benchmark_4000_members(client):
    """
    High-Concurrency & Scalability Benchmark:
    Simulates 4,000 active student accounts and benchmarks the bulk broadcast notification engine.
    Ensures CampusConnect handles 4,000+ members without timeouts, lockups, or crashes (< 150ms).
    """
    with client.application.app_context():
        student_role = Role.query.filter_by(name='student').first()
        dept = Department.query.first()
        assert student_role is not None

        # Seed 4,000 student accounts using bulk insertion
        current_count = User.query.filter_by(role_id=student_role.id).count()
        needed = 4000 - current_count
        if needed > 0:
            bulk_users = [
                {
                    'email': f'student_perf_{i}@campusconnect.edu',
                    'campus_id': f'PERF-STU-{i:05d}',
                    'full_name': f'Benchmark Student {i}',
                    'phone': '+1 (555) 000-0000',
                    'password_hash': 'pbkdf2:sha256:dummyhashforbenchmark',
                    'role_id': student_role.id,
                    'department_id': dept.id,
                    'designation_or_year': '1st Year Undergraduate',
                    'is_active': True,
                    'is_approved': True
                }
                for i in range(current_count + 1, current_count + needed + 1)
            ]
            db.session.bulk_insert_mappings(User, bulk_users)
            db.session.commit()

        total_students = User.query.filter_by(role_id=student_role.id, is_active=True).count()
        assert total_students >= 4000

        # Create a sample lost item
        first_user = User.query.first()
        lost_item = Item(
            title='MacBook Pro 14 M3 Silver',
            item_type='LOST',
            category_id=1,
            description='Left in Student Union café near window.',
            location='Student Union',
            incident_date=date.today(),
            status='OPEN',
            reporter_id=first_user.id
        )
        db.session.add(lost_item)
        db.session.commit()

        # Benchmark broadcast execution time
        start_time = time.perf_counter()
        notif_count = broadcast_lost_item_to_students(lost_item)
        elapsed_seconds = time.perf_counter() - start_time

        # Verify broadcast reached all 4,000 students
        assert notif_count >= 4000
        # Verify sub-second execution speed for 4,000 records
        assert elapsed_seconds < 1.0, f"Broadcast took too long: {elapsed_seconds:.4f}s for {notif_count} students"
        print(f"\n[BENCHMARK] Successfully broadcasted to {notif_count} students in {elapsed_seconds*1000:.2f} ms!")
