import pytest
from playwright.sync_api import sync_playwright


def test_landing_page_and_navigation(live_server):
    """Test landing page renders properly, search bar functions, and navigation links work."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # 1. Visit landing page
        page.goto(f"{live_server}/")
        assert "CampusConnect" in page.title()
        assert page.locator("text=Official Campus Property Network").is_visible()

        # 2. Check search bar
        search_input = page.locator("input[name='keyword']")
        assert search_input.is_visible()
        search_input.fill("MacBook")
        page.locator("button:has-text('Search')").click()

        # Verify search results page loaded
        page.wait_for_load_state("networkidle")
        assert "Browse Lost Items" in page.content()
        assert "MacBook" in page.content()

        browser.close()


def test_student_login_and_dashboard_workflow(live_server):
    """Test student login, redirect to student dashboard, and view metrics."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Visit login page
        page.goto(f"{live_server}/auth/login")
        assert "Sign In" in page.title()

        # Fill login form
        page.fill("input[name='email']", "student@campusconnect.edu")
        page.fill("input[name='password']", "Student@2026!")
        page.click("button:has-text('Sign In')")

        page.wait_for_load_state("networkidle")

        # Verify arrival at student dashboard
        assert "Student Dashboard" in page.title()
        assert "Jordan Lee" in page.content()
        assert "My Reported Items" in page.content()

        # Check navigation dropdown and sign out
        page.goto(f"{live_server}/auth/logout")
        page.wait_for_load_state("networkidle")
        assert "signed out safely" in page.content()

        browser.close()


def test_admin_portal_workflow(live_server):
    """Test admin authentication and oversight portal access."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Sign in as administrator
        page.goto(f"{live_server}/auth/login")
        page.fill("input[name='email']", "admin@campusconnect.edu")
        page.fill("input[name='password']", "Admin@2026!")
        page.click("button:has-text('Sign In')")

        page.wait_for_load_state("networkidle")

        # Verify admin dashboard
        assert "Administrator Oversight" in page.title()
        assert "User Governance" in page.content()

        # Navigate to Users management page
        page.goto(f"{live_server}/admin/users")
        page.wait_for_load_state("networkidle")
        assert "User Management" in page.title()
        assert "student@campusconnect.edu" in page.content()

        # Navigate to Items moderation page
        page.goto(f"{live_server}/admin/items")
        page.wait_for_load_state("networkidle")
        assert "Item Moderation" in page.title()

        browser.close()


def test_mobile_responsive_viewport(live_server):
    """Test responsive design rendering at mobile viewport (iPhone 13 / 390x844)."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Emulate mobile screen
        context = browser.new_context(viewport={'width': 390, 'height': 844}, is_mobile=True)
        page = context.new_page()

        page.goto(f"{live_server}/")
        page.wait_for_load_state("networkidle")

        # Verify mobile hamburger menu toggle is visible
        toggler = page.locator(".navbar-toggler")
        assert toggler.is_visible()

        # Open navbar menu
        toggler.click()
        page.wait_for_timeout(300)
        
        # Verify navigation link in navbar menu is visible
        nav_link = page.locator("#navbarContent a[href*='/items/lost']")
        assert nav_link.is_visible()

        browser.close()
