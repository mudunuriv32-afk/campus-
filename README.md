# CampusConnect: Campus Lost & Found Management Portal

[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.14-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.1-black.svg)](https://flask.palletsprojects.com/)
[![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3-purple.svg)](https://getbootstrap.com/)
[![Tests](https://img.shields.io/badge/Tests-65%20Passed%20(100%25)-brightgreen.svg)]()
[![License](https://img.shields.io/badge/License-MIT-blue.svg)]()

**CampusConnect** is a centralized, secure digital lost-and-found management platform designed for university campuses. It streamlines the lifecycle of lost belongings—from instant reporting and automated correlation matching to cryptographically hashed proof verification, structured claim approval workflows, and administrative governance.

---

## 🏛️ System Architecture

CampusConnect follows a clean service-oriented MVC architecture:

```
CampusConnect/
├── app/
│   ├── __init__.py           # Application Factory & Security Headers
│   ├── config.py             # Multi-environment configuration (Dev, Test, Prod)
│   ├── extensions.py         # SQLAlchemy ORM, Flask-Migrate, Flask-WTF CSRF
│   ├── seed.py               # Database seeder (Roles, Departments, Categories, Seed Accounts)
│   ├── models/               # Relational database models
│   │   ├── user.py           # User, Role, Department (RBAC & College ID auth)
│   │   ├── item.py           # Item, ItemCategory, ItemImage
│   │   ├── claim.py          # Claim (State machine: PENDING, APPROVED, REJECTED, CANCELLED)
│   │   ├── notification.py   # In-app user notifications
│   │   ├── audit.py          # Administrative & Security Audit Logs
│   │   ├── settings.py       # Dynamic platform settings key-value store
│   │   └── password_reset.py # PasswordResetRecord (Audit trail, state lifecycle & expiry)
│   ├── forms/                # WTForms with strict server-side validation & regex
│   │   ├── auth_forms.py     # Registration, Login, Password Change/Forgot, Temp Password
│   │   ├── item_forms.py     # Lost/Found Item Reporting, Filtering & Edit
│   │   ├── claim_forms.py    # Claim submission & Review remarks
│   │   ├── admin_forms.py    # College ID search & temporary password reset confirmation
│   │   └── profile_forms.py  # Profile edit & secure profile photo upload
│   ├── services/             # Core business logic layer
│   │   ├── auth_service.py   # RBAC decorators, rate limiting & session caching
│   │   ├── password_reset_service.py # Admin temp password reset & mandatory password change
│   │   ├── item_service.py   # Smart item search & suggestion correlation engine
│   │   ├── claim_service.py  # Atomic claim transaction state machine
│   │   ├── notification_service.py # In-app notification dispatcher
│   │   └── upload_service.py # Magic bytes validation & secure file handling
│   ├── routes/               # Blueprints
│   │   ├── main.py           # Landing page, About, FAQs, Contact & Help, Legal
│   │   ├── auth.py           # Student & Staff auth, dual login, mandatory password change
│   │   ├── items.py          # Lost & Found catalogues, reporting, editing, details
│   │   ├── claims.py         # Claim requests, claimant management, review actions
│   │   ├── dashboard.py      # Student & Staff metrics, notifications, verified student profile
│   │   └── admin.py          # Governance, user toggle, item moderation, reset portal, student search
│   ├── static/               # Collegiate Navy theme & JavaScript assets
│   │   ├── css/main.css      # Custom styling, dark navy palettes, responsive cards
│   │   ├── js/app.js         # Interactive toast alerts, image preview, confirmation dialogs
│   │   └── images/           # Default avatar, logos, and UI visual assets
│   └── templates/            # 32 Jinja2 templates (Semantic HTML5 & Accessible)
├── migrations/               # Alembic database migration scripts
├── tests/                    # Full automated test suite (51 tests)
│   ├── conftest.py           # Session & autouse test fixtures with clean DB isolation
│   ├── test_auth.py          # Authentication, password rules, role permissions
│   ├── test_items.py         # Reporting, editing, IDOR prevention, search & filtering
│   ├── test_claims.py        # Claim lifecycle, approval transactions, anti-duplicate rules
│   ├── test_admin.py         # Admin oversight, role toggle, audit logs, platform settings
│   ├── test_security.py      # Security headers, file magic bytes, rate limiting
│   ├── test_password_reset.py # Module 20: 14 tests for admin temp password reset & College ID auth
│   └── e2e/                  # End-to-end browser tests (Playwright Chromium)
│       ├── conftest.py       # Live server background thread fixture
│       ├── test_e2e_workflows.py # Real Playwright Chromium student & staff workflows
│       └── test_password_reset_e2e.py # Real Playwright Chromium temporary password E2E flow
├── Procfile                  # Production process definition (Render / Heroku)
├── gunicorn.conf.py          # Gunicorn WSGI production web server configuration
├── wsgi.py                   # WSGI production entrypoint
├── requirements.txt          # Frozen application dependencies
└── README.md                 # System documentation
```

---

## 👥 User Roles & Access Control

CampusConnect enforces strict Server-Side Role-Based Access Control (RBAC):

| Role | Key Capabilities |
| :--- | :--- |
| **Student** | Report lost/found items, view details, file claims on found items, review claims on self-reported items, receive in-app notifications, view personal recovery dashboard. |
| **Staff / Faculty** | All student capabilities, plus custodian verification, item inventory management, priority claim approval, and department item custody logging. |
| **Administrator** | Complete portal governance: activate/deactivate accounts, approve staff registrations, unflag/remove inappropriate items, review claims, manage categories, inspect audit logs, and update platform configuration. |

### Default Seed Accounts

The platform includes verified demo accounts for testing and evaluation:

* **Administrator**: `admin@campusconnect.edu` (Password: `Admin@2026!`)
* **Staff Member**: `staff@campusconnect.edu` (Password: `Staff@2026!`)
* **Student User**: `student@campusconnect.edu` (Password: `Student@2026!`)
* **Student User (Peer)**: `samantha@campusconnect.edu` (Password: `Student@2026!`)

---

## ⚙️ Smart Correlation Engine

When viewing any item listing, CampusConnect automatically computes prospective correlations between lost and found listings:
1. **Opposite Classification**: Matches `LOST` reports against `FOUND` items and vice versa.
2. **Category Equivalence**: Prioritizes identical categories (e.g., *Electronics* $\leftrightarrow$ *Electronics*).
3. **Keyword Proximity**: Compares title and description tokens against location cues and feature signatures.
4. **Temporal Affinity**: Filters candidates within proximate date windows (default within 14 days).
5. **Privacy Safe**: Identifying attributes and phone numbers remain masked until an authorized claim is formally approved by the owner.

---

## 🔒 Security Hardening

* **OWASP Headers**: `Content-Security-Policy`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: SAMEORIGIN`, `X-XSS-Protection: 1; mode=block`, `Referrer-Policy: strict-origin-when-cross-origin`.
* **Deep File Inspection**: Uploaded images are strictly verified via Pillow binary magic bytes analysis (checking true `PNG`, `JPEG`, or `WEBP` headers) rather than trusting client file extensions.
* **UUID Storage**: Filenames are cryptographically randomized with UUIDs and stored outside executable code paths.
* **Brute-Force Rate Limiting**: Sensitive endpoints (authentication, claim filings) enforce IP-keyed leaky bucket rate limiting.
* **State Machine Atomicity**: Claim approvals and item status transitions occur within atomic SQLAlchemy database transactions with rollback guards.
* **CSRF & IDOR Prevention**: Every state-changing form is protected by Flask-WTF CSRF tokens; item editing and claim cancellations verify ownership on the server side before dispatching views.

---

## 🔑 Module 20: Admin Password Reset Portal & Student Identity System

CampusConnect features a secure, enterprise-grade administrative password management and student directory subsystem:

### 1. Dual Authentication (College ID & Email)
Students, faculty, and administrators can authenticate using either their official **College Email** (`student@campusconnect.edu`) or their registered **College ID / Student ID / Campus ID** (`STU2026001`), verified case-insensitively with Werkzeug-hashed security.

### 2. Admin-Controlled Password Reset Portal (`/admin/password-reset`)
* **Target User Lookup**: Search by College ID or Student ID to retrieve user card (name, institutional ID, registered email, department, account status) without ever disclosing passwords.
* **Confirmation Guard**: Trigger modal confirmation before issuing a reset.
* **Cryptographic Generation**: Creates an unguessable 12-character random temporary password (`secrets.choice` with letters, digits, and special characters).
* **One-Time Administrator Reveal**: Revealed strictly once in session with a one-click clipboard copy tool. Plaintext is never saved in the database or logs.
* **15-Minute Expiry**: Temporary passwords expire automatically after 15 minutes.
* **Historical Audit Trail**: Tracks Reset ID, User ID, Admin ID, timestamps, expiry, and resolution status (`ACTIVE`, `COMPLETED`, `EXPIRED`, `SUPERSEDED`).

### 3. Mandatory Password Change Interception (`/change-temporary-password`)
* When an administrator resets an account, `force_password_change` is set to `True`.
* Upon logging in with the temporary password, the user is immediately redirected to `/change-temporary-password`.
* Strict route decorators intercept attempts to access student or staff dashboards until the change is satisfied.
* Enforces password complexity rules and blocks reuse of the temporary password.
* Upon submission, the new password is hashed, temporary credentials invalidated, active sessions refreshed, and the user routed to their respective dashboard.

### 4. Student Management & Verification Directory (`/admin/students`)
* Dedicated administrator console to inspect student accounts by College ID.
* Review real-time student activity: reported lost belongings, found submissions, active claims, and claim resolutions.
* One-click toggle for administrative deactivation/reactivation of student accounts.

### 5. Verified Student Profile Management (`/profile`, `/dashboard/profile`)
* Displays immutable institutional identity records (Full Name, College ID, College Email, Academic Department).
* Allows updating emergency contact phone numbers with international format validation.
* Secure profile photo uploads inspected via Pillow binary magic bytes analysis.

### 6. Interactive Admin Analytics Dashboard (`/admin/dashboard`)
* Responsive Chart.js visual telemetry tracking Lost vs. Found distribution across 11 campus categories.
* Claim status doughnut metrics monitoring resolution rates in real time.

---

## 🚀 Quickstart & Local Setup

### 1. Clone & Set Up Environment

```bash
git clone <repository-url>
cd CampusConnect

# Create and activate Python virtual environment
python -m venv venv

# Windows (PowerShell)
.\venv\Scripts\Activate.ps1

# Linux / macOS
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file in the project root:

```env
FLASK_CONFIG=development
SECRET_KEY=campusconnect-production-secret-key-change-me
DATABASE_URL=sqlite:///instance/campusconnect.db
UPLOAD_FOLDER=app/static/uploads
MAX_CONTENT_LENGTH=5242880
SESSION_COOKIE_SECURE=False
```

### 3. Initialize Database & Seed Demo Data

```bash
flask init-db
flask seed-data
```

### 4. Run Development Server

```bash
flask run --port 5000
```
Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser.

---

## 🧪 Automated Testing

### Run Backend Unit & Integration Tests (pytest)
```bash
# Core platform test suites (Auth, Items, Claims, Admin, Security)
pytest tests/test_auth.py tests/test_items.py tests/test_claims.py tests/test_admin.py tests/test_security.py -v

# Module 20: Admin Password Reset, College ID Auth, Mandatory Password Change (14 tests)
pytest tests/test_password_reset.py -v
```

### Run Playwright End-to-End Browser Tests
```bash
# Ensure Playwright browser binaries are installed
playwright install chromium

# Run core browser test suite (student & staff workflows)
pytest tests/e2e/test_e2e_workflows.py -v

# Run Module 20 browser test (Admin reset & temporary password change workflow)
pytest tests/e2e/test_password_reset_e2e.py -v
```

### Run All 65 Tests Together
```bash
pytest -v
```

---

## 🌐 Production Deployment (Render Guide)

### 1. Step-by-Step Render Setup

1. **Sign in to Render**: Navigate to [https://dashboard.render.com](https://dashboard.render.com).
2. **Create PostgreSQL Database**:
   * Click **New +** $\rightarrow$ **PostgreSQL**.
   * **Name**: `campusconnect-db`
   * **Database**: `campusconnect_db`
   * **User**: `campusconnect_user`
   * **Region**: Choose closest to you (e.g. *Oregon (US West)* or *Frankfurt (EU)*).
   * Once created, scroll to **Connections** and copy either:
     * **External Database URL** (Recommended — resolves everywhere including across regions):
       `postgresql://campusconnect_user:PASSWORD@dpg-xxxx-a.oregon-postgres.render.com/campusconnect_db`
     * **Internal Database URL** (Private network):
       `postgresql://campusconnect_user:PASSWORD@dpg-xxxx-a/campusconnect_db`
3. **Create Web Service**:
   * Click **New +** $\rightarrow$ **Web Service**.
   * Under **Build and deploy from a Git repository**, connect your GitHub account or paste:
     **Git Repository URL**: `https://github.com/mudunuriv32-afk/campus-.git`
   * **Branch**: `main`
   * **Runtime**: `Python 3`
   * **Build Command**: `pip install -r requirements.txt`
   * **Start Command**: `gunicorn wsgi:app --config gunicorn.conf.py`
   *(Note: The database tables and seed data are automatically initialized on startup by `wsgi.py`, so you do NOT need database commands in your Build Command!)*

### 2. Environment Variables to Paste in Render

In your Render Web Service dashboard, go to **Environment** $\rightarrow$ **Add Environment Variable**:

| Variable Key | Value to Paste in Render | Purpose |
| :--- | :--- | :--- |
| `FLASK_CONFIG` | `production` | Enables production hardening and error masking |
| `SECRET_KEY` | `d10b4b7564b5f3bffd858fdd6db43b48a0425e1242ba446a8094b97b89102e29` | Cryptographic secret for signing sessions & CSRF |
| `DATABASE_URL` | *Paste your Render or Supabase PostgreSQL URL* | Connects to PostgreSQL database |
| `SESSION_COOKIE_SECURE` | `True` | Enforces HTTPS-only secure cookies |
| `GUNICORN_WORKER_CLASS`| `gthread` | High-concurrency threaded workers |
| `GUNICORN_THREADS` | `4` | 4 worker threads per worker process |
| `WEB_CONCURRENCY` | `2` | 2 worker processes |
| `MAX_CONTENT_LENGTH` | `5242880` | Restricts file uploads to 5MB max |
| `CLOUDINARY_URL` *(Optional)* | `cloudinary://API_KEY:API_SECRET@CLOUD_NAME` | Permanent cloud image storage |

### 3. Using Supabase & Cloudinary (Optional)

* **Supabase PostgreSQL (Recommended for Free Tier)**:
  Instead of Render PostgreSQL, you can use Supabase's generous free tier:
  1. Create a free project at [https://supabase.com](https://supabase.com).
  2. For cloud platforms like Render that use IPv4, use the **Supabase Connection Pooler URI**:
     ```text
     postgresql://postgres.<PROJECT_REF>:<PASSWORD>@aws-0-<REGION>.pooler.supabase.com:5432/postgres
     ```
     *(Example: `postgresql://postgres.qzeaxacyehcupzhgjxyk:q3iHwZ7y6VMHNdnz@aws-0-ap-northeast-2.pooler.supabase.com:5432/postgres`)*
  3. Paste that URI into Render's `DATABASE_URL` environment variable.
* **Cloudinary Storage (Persistent Cloud Photos)**:
  1. Create a free account at [https://cloudinary.com](https://cloudinary.com).
  2. Copy your **API Environment Variable** (`cloudinary://...`).
  3. Add `CLOUDINARY_URL` to your Render environment variables. All uploads will automatically be delivered via Cloudinary CDN!

### 4. Verified Demo Accounts (Pre-Seeded)

Once deployed, the following demo accounts are immediately ready for testing:

| Role | Login Identifier (Email or College ID) | Password | Privileges |
| :--- | :--- | :--- | :--- |
| **Platform Administrator** | `admin@campusconnect.edu` or `ADM-1001` | `Admin@2026!` | Full Admin Portal, Password Resets, User Management |
| **Faculty / Staff** | `staff@campusconnect.edu` or `STF-2001` | `Staff@2026!` | Item Custody, Claims Review & Approval |
| **Student 1** | `jordan@campusconnect.edu` or `STU-3001` | `Student@2026!` | Report Lost/Found, Submit Claims, Profile Management |
| **Student 2** | `samantha@campusconnect.edu` or `STU-3002` | `Student@2026!` | Student Reporting & Recovery Privileges |

### 5. URLs Summary for Render

* **GitHub Repository URL**: `https://github.com/mudunuriv32-afk/campus-.git`
* **Health Check Probe**: `https://<your-service-name>.onrender.com/health` (returns JSON status)
* **Live Web Portal**: `https://<your-service-name>.onrender.com`

---

## 📜 License & Compliance

CampusConnect is released under the **MIT License**. Engineered for campus safety, data privacy, and accessible student recovery operations.
