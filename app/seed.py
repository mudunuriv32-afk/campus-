from app.extensions import db
from app.models.user import Role, Department, User
from app.models.item import ItemCategory, Item, ItemImage
from app.models.settings import PlatformSetting
from datetime import date, datetime, timezone, timedelta


def seed_database():
    """Seed standard roles, departments, item categories, platform settings, and verified accounts."""
    # 1. Roles
    roles = [
        ('student', 'University student with lost & found reporting and claiming privileges'),
        ('staff', 'Faculty or staff member with item custody and moderation privileges'),
        ('admin', 'Platform administrator with complete oversight and user governance')
    ]
    role_map = {}
    for name, desc in roles:
        r = Role.query.filter_by(name=name).first()
        if not r:
            r = Role(name=name, description=desc)
            db.session.add(r)
            db.session.flush()
        role_map[name] = r

    # 2. Departments
    departments = [
        ('Computer Science & Engineering', 'CSE'),
        ('Electrical & Electronics Engineering', 'EEE'),
        ('Mechanical Engineering', 'ME'),
        ('Business Administration', 'MBA'),
        ('Campus Administration & Security', 'CAS'),
        ('Library & Information Services', 'LIS'),
        ('General Sciences & Humanities', 'GSH')
    ]
    dept_map = {}
    for name, code in departments:
        d = Department.query.filter_by(code=code).first()
        if not d:
            d = Department(name=name, code=code)
            db.session.add(d)
            db.session.flush()
        dept_map[code] = d

    # 3. Item Categories
    categories = [
        ('Electronics', 'Headphones, chargers, USB drives, power banks', 'bi-cpu'),
        ('Mobile Phones', 'Smartphones, feature phones, cases', 'bi-phone'),
        ('Laptops', 'Laptops, tablets, chargers, sleeves', 'bi-laptop'),
        ('Books', 'Textbooks, notebooks, course binders, novels', 'bi-book'),
        ('ID Cards', 'Student IDs, faculty cards, library cards, driver licenses', 'bi-person-badge'),
        ('Wallets', 'Wallets, coin purses, cardholders', 'bi-wallet2'),
        ('Keys', 'Dorm keys, bike keys, car key fobs, locker keys', 'bi-key'),
        ('Bags', 'Backpacks, tote bags, gym bags, laptop cases', 'bi-backpack'),
        ('Clothing', 'Jackets, hoodies, caps, scarves, lab coats', 'bi-tag'),
        ('Accessories', 'Watches, eyeglasses, sunglasses, jewelry', 'bi-watch'),
        ('Other', 'Water bottles, umbrella, sports equipment, musical instruments', 'bi-box-seam')
    ]
    cat_map = {}
    for name, desc, icon in categories:
        c = ItemCategory.query.filter_by(name=name).first()
        if not c:
            c = ItemCategory(name=name, description=desc, icon=icon)
            db.session.add(c)
            db.session.flush()
        cat_map[name] = c

    # 4. Platform Settings
    settings = [
        ('campus_name', 'Metropolitan University', 'Official campus identity'),
        ('security_office_location', 'Main Gate Security Center, Ground Floor Block A', 'Physical drop-off office'),
        ('support_email', 'help@campusconnect.edu', 'Helpdesk inquiry email'),
        ('retention_period_days', '90', 'Days before unclaimed items are archived'),
        ('require_staff_approval', 'True', 'Require admin review for new staff accounts')
    ]
    for key, val, desc in settings:
        PlatformSetting.set(key, val, desc)

    # 5. Seed Users
    # Admin User
    admin = User.query.filter_by(email='admin@campusconnect.edu').first()
    if not admin:
        admin = User(
            email='admin@campusconnect.edu',
            full_name='Campus Administrator',
            campus_id='ADM-1001',
            phone='+1-555-0101',
            role_id=role_map['admin'].id,
            department_id=dept_map['CAS'].id,
            designation_or_year='Chief Security Officer',
            is_active=True,
            is_approved=True
        )
        admin.set_password('Admin@2026!')
        db.session.add(admin)
        db.session.flush()

    # Staff User
    staff = User.query.filter_by(email='staff@campusconnect.edu').first()
    if not staff:
        staff = User(
            email='staff@campusconnect.edu',
            full_name='Prof. Marcus Vance',
            campus_id='STF-2001',
            phone='+1-555-0102',
            role_id=role_map['staff'].id,
            department_id=dept_map['CSE'].id,
            designation_or_year='Associate Professor / Lab In-Charge',
            is_active=True,
            is_approved=True
        )
        staff.set_password('Staff@2026!')
        db.session.add(staff)
        db.session.flush()

    # Student 1 (Jordan)
    student1 = User.query.filter_by(email='student@campusconnect.edu').first()
    if not student1:
        student1 = User(
            email='student@campusconnect.edu',
            full_name='Jordan Lee',
            campus_id='STU-3001',
            phone='+1-555-0103',
            role_id=role_map['student'].id,
            department_id=dept_map['CSE'].id,
            designation_or_year='3rd Year Undergraduate',
            is_active=True,
            is_approved=True
        )
        student1.set_password('Student@2026!')
        db.session.add(student1)
        db.session.flush()

    # Student 2 (Samantha)
    student2 = User.query.filter_by(email='samantha@campusconnect.edu').first()
    if not student2:
        student2 = User(
            email='samantha@campusconnect.edu',
            full_name='Samantha Patel',
            campus_id='STU-3002',
            phone='+1-555-0104',
            role_id=role_map['student'].id,
            department_id=dept_map['MBA'].id,
            designation_or_year='2nd Year Graduate',
            is_active=True,
            is_approved=True
        )
        student2.set_password('Student@2026!')
        db.session.add(student2)
        db.session.flush()

    # 6. Seed initial realistic items for demonstration
    existing_items = Item.query.count()
    if existing_items == 0:
        sample_items = [
            Item(
                title='Silver Apple MacBook Air 13-inch',
                item_type='LOST',
                category_id=cat_map['Laptops'].id,
                description='Left on the second floor study cubicles in Main Library. Has a blue NASA sticker on the top cover.',
                identifying_features='Serial ends in X7Y9, desktop wallpaper is Yosemite valley, user account named Jordan.',
                location='Main Campus Library - 2nd Floor Quiet Study',
                incident_date=date.today() - timedelta(days=1),
                contact_preference='IN_APP',
                status='OPEN',
                reporter_id=student1.id
            ),
            Item(
                title='Navy Blue Dell Backpack with Notebooks',
                item_type='LOST',
                category_id=cat_map['Bags'].id,
                description='Left behind near Lecture Hall 104 after Algorithms class. Contains spiral notebooks and scientific calculator.',
                identifying_features='Silver keychain with initial "J" attached to main zipper.',
                location='Engineering Block B - Lecture Hall 104',
                incident_date=date.today() - timedelta(days=2),
                contact_preference='IN_APP',
                status='OPEN',
                reporter_id=student1.id
            ),
            Item(
                title='Found: Stainless Steel Hydro Flask (Blue)',
                item_type='FOUND',
                category_id=cat_map['Other'].id,
                description='Found on the bench outside Student Union cafeteria. Has minor scuffs on the bottom edge.',
                identifying_features='Has an outdoor hiking decal on the back side.',
                location='Student Union Cafeteria Bench',
                incident_date=date.today(),
                contact_preference='IN_APP',
                status='OPEN',
                reporter_id=staff.id
            ),
            Item(
                title='Found: Set of Dorm & Bike Keys on Leather Lanyard',
                item_type='FOUND',
                category_id=cat_map['Keys'].id,
                description='Found on the sidewalk between Oak Hall and Dining Commons. Handed in to Security Desk.',
                identifying_features='Three brass keys, one black Kryptonite bike lock key, brown leather loop.',
                location='Walkway near Oak Hall Dormitory',
                incident_date=date.today() - timedelta(days=1),
                contact_preference='IN_APP',
                status='OPEN',
                reporter_id=admin.id
            )
        ]
        db.session.add_all(sample_items)

    db.session.commit()
