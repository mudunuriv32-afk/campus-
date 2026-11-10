import pytest
from playwright.sync_api import sync_playwright


def test_e2e_admin_password_reset_and_mandatory_change(live_server):
    """
    Complete end-to-end browser test:
    1. Admin navigates to Password Reset Portal.
    2. Searches student by College ID (STU-3001).
    3. Confirms and generates 15m temporary credential.
    4. Copies/extracts the revealed one-time temporary password.
    5. Admin signs out.
    6. Student signs in using College ID and the temporary password.
    7. Forced redirect to mandatory password change screen (/change-temporary-password).
    8. Student enters temp password and sets new strong permanent password.
    9. Student is redirected to Student Dashboard.
    10. Student checks /profile and verifies immutable identity.
    11. Student signs out and signs back in with the new permanent password.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Step 1: Admin Login
        page.goto(f"{live_server}/auth/login")
        page.fill("input[name='email']", "admin@campusconnect.edu")
        page.fill("input[name='password']", "Admin@2026!")
        page.click("button:has-text('Sign In')")
        page.wait_for_load_state("networkidle")

        assert "Administrator Oversight" in page.title()

        # Step 2: Navigate to Admin Password Reset Portal
        page.goto(f"{live_server}/admin/password-reset")
        page.wait_for_load_state("networkidle")
        assert "Password Reset Portal" in page.title()
        assert page.locator("text=Admin-Controlled Password Reset Portal").is_visible()

        # Step 3: Search Student by College ID
        page.fill("input[name='college_id']", "STU-3001")
        page.click("#searchUserBtn")
        page.wait_for_load_state("networkidle")

        # Verify target user card is displayed
        assert "Jordan Lee" in page.content()
        assert "STU-3001" in page.content()
        assert "student@campusconnect.edu" in page.content()

        # Step 4: Click Generate Temporary Password button to open confirmation modal
        page.click("#initiateResetBtn")
        page.wait_for_selector("#confirmResetModal.show", state="visible")

        # Confirm generation in modal
        page.click("#confirmGenerateBtn")
        page.wait_for_load_state("networkidle")

        # Step 5: Verify One-Time Temporary Password is revealed
        temp_pw_input = page.locator("#revealedTempPassword")
        assert temp_pw_input.is_visible()
        temp_pw = temp_pw_input.input_value()
        assert len(temp_pw) >= 12

        # Step 6: Admin Signs Out
        page.goto(f"{live_server}/auth/logout")
        page.wait_for_load_state("networkidle")

        # Step 7: Student Signs In with College ID and Temporary Password
        page.goto(f"{live_server}/auth/login")
        page.fill("input[name='email']", "STU-3001")
        page.fill("input[name='password']", temp_pw)
        page.click("button:has-text('Sign In')")
        page.wait_for_load_state("networkidle")

        # Step 8: Verify forced redirect to /change-temporary-password
        assert "/change-temporary-password" in page.url
        assert "Set Permanent Password" in page.content()

        # Test restriction: attempt to bypass by going to items or dashboard
        page.goto(f"{live_server}/dashboard/student")
        page.wait_for_load_state("networkidle")
        assert "/change-temporary-password" in page.url

        # Step 9: Fill out mandatory password change form
        new_permanent_pw = "JordanSecure2026!#"
        page.fill("input[name='temp_password']", temp_pw)
        page.fill("input[name='new_password']", new_permanent_pw)
        page.fill("input[name='confirm_password']", new_permanent_pw)
        page.click("button:has-text('Set Password and Continue')")
        page.wait_for_load_state("networkidle")

        # Verify arrival at student dashboard
        assert "/dashboard/student" in page.url or "Student Dashboard" in page.title()
        assert "permanent password has been set successfully" in page.content()

        # Step 10: Visit Student Profile
        page.goto(f"{live_server}/dashboard/profile")
        page.wait_for_load_state("networkidle")
        assert "Institutional Student Identity" in page.content()
        assert "STU-3001" in page.content()

        # Update contact phone
        page.fill("input[name='phone']", "+1 (555) 987-6543")
        page.click("button:has-text('Save Contact Info')")
        page.wait_for_load_state("networkidle")
        assert "Contact phone number updated successfully" in page.content()

        # Step 11: Sign out and verify login with new permanent password
        page.goto(f"{live_server}/auth/logout")
        page.wait_for_load_state("networkidle")

        page.goto(f"{live_server}/auth/login")
        page.fill("input[name='email']", "STU-3001")
        page.fill("input[name='password']", new_permanent_pw)
        page.click("button:has-text('Sign In')")
        page.wait_for_load_state("networkidle")

        assert "Welcome back, Jordan Lee!" in page.content()

        browser.close()
