// CampusConnect Interactive Enhancements
document.addEventListener('DOMContentLoaded', function () {
  // Initialize Bootstrap Tooltips
  const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
  tooltipTriggerList.map(function (tooltipTriggerEl) {
    return new bootstrap.Tooltip(tooltipTriggerEl);
  });

  // Auto-dismiss Flash Alerts after 5 seconds (except danger alerts)
  const alerts = document.querySelectorAll('.alert:not(.alert-danger)');
  alerts.forEach(function (alert) {
    setTimeout(function () {
      const bsAlert = new bootstrap.Alert(alert);
      bsAlert.close();
    }, 5000);
  });

  // Image Upload Live Preview
  const imageInputs = document.querySelectorAll('input[type="file"][accept*="image"], input[type="file"]');
  imageInputs.forEach(function (input) {
    input.addEventListener('change', function (e) {
      const file = e.target.files[0];
      if (file) {
        // Enforce 5MB size limit client-side
        if (file.size > 5 * 1024 * 1024) {
          alert('File is too large! Maximum allowed image size is 5MB.');
          input.value = '';
          return;
        }

        const previewContainer = document.getElementById(input.id + '-preview');
        if (previewContainer) {
          const reader = new FileReader();
          reader.onload = function (evt) {
            previewContainer.innerHTML = `
              <div class="mt-2 text-center">
                <img src="${evt.target.result}" class="img-thumbnail" style="max-height: 180px; object-fit: contain;">
                <div class="small text-muted mt-1">${file.name} (${(file.size / 1024).toFixed(1)} KB)</div>
              </div>
            `;
          };
          reader.readAsDataURL(file);
        }
      }
    });
  });

  // Dynamic Confirmation Modals for Destructive or Important Actions
  const confirmActions = document.querySelectorAll('[data-confirm]');
  confirmActions.forEach(function (element) {
    element.addEventListener('click', function (e) {
      const message = element.getAttribute('data-confirm') || 'Are you sure you want to perform this action?';
      if (!confirm(message)) {
        e.preventDefault();
      }
    });
  });

  // Universal Top Navbar Refresh Button
  const globalRefreshBtn = document.getElementById('globalRefreshBtn');
  if (globalRefreshBtn) {
    globalRefreshBtn.addEventListener('click', function () {
      const icon = document.getElementById('refreshIcon') || globalRefreshBtn.querySelector('i');
      if (icon) {
        icon.classList.add('cc-spin');
      }
      globalRefreshBtn.disabled = true;
      // Perform clean refresh bypassing browser cache
      window.location.reload();
    });
  }

  // Password Show / Hide Visibility Eye Toggle
  const toggleButtons = document.querySelectorAll('.btn-password-toggle');
  toggleButtons.forEach(function (btn) {
    btn.addEventListener('click', function () {
      const targetId = btn.getAttribute('data-target');
      const input = targetId ? document.getElementById(targetId) : btn.closest('.input-group')?.querySelector('input');
      if (!input) return;

      const icon = btn.querySelector('i');
      if (input.type === 'password') {
        input.type = 'text';
        if (icon) {
          icon.classList.remove('bi-eye');
          icon.classList.add('bi-eye-slash');
        }
        btn.setAttribute('aria-label', 'Hide password');
        btn.setAttribute('title', 'Hide password');
      } else {
        input.type = 'password';
        if (icon) {
          icon.classList.remove('bi-eye-slash');
          icon.classList.add('bi-eye');
        }
        btn.setAttribute('aria-label', 'Show password');
        btn.setAttribute('title', 'Show password');
      }
    });
  });

  // Password Live Confirmation Matching Indicator
  const confirmPwdInput = document.querySelector('input[name="confirm_password"], #confirm_password');
  const mainPwdInput = document.querySelector('input[name="new_password"], #new_password, input[name="password"], #password');
  const matchIndicator = document.getElementById('password-match-indicator');

  function checkPasswordMatch() {
    if (!confirmPwdInput || !mainPwdInput || !matchIndicator) return;

    const pwdVal = mainPwdInput.value;
    const confirmVal = confirmPwdInput.value;

    if (!confirmVal) {
      matchIndicator.innerHTML = '';
      matchIndicator.className = 'password-match-badge d-none';
      return;
    }

    if (pwdVal === confirmVal) {
      matchIndicator.className = 'password-match-badge matched d-inline-flex';
      matchIndicator.innerHTML = '<i class="bi bi-check-circle-fill"></i> Passwords match perfectly';
    } else {
      matchIndicator.className = 'password-match-badge mismatched d-inline-flex';
      matchIndicator.innerHTML = '<i class="bi bi-x-circle-fill"></i> Passwords do not match';
    }
  }

  if (confirmPwdInput && mainPwdInput && matchIndicator) {
    confirmPwdInput.addEventListener('input', checkPasswordMatch);
    mainPwdInput.addEventListener('input', checkPasswordMatch);
  }

  // Live Password Strength & Requirements Checklist
  const passwordRules = {
    length: document.getElementById('rule-length'),
    cases: document.getElementById('rule-cases'),
    number: document.getElementById('rule-number'),
    symbol: document.getElementById('rule-symbol')
  };

  if (mainPwdInput && (passwordRules.length || passwordRules.cases || passwordRules.number || passwordRules.symbol)) {
    mainPwdInput.addEventListener('input', function () {
      const val = mainPwdInput.value;

      function updateRule(element, isValid) {
        if (!element) return;
        const icon = element.querySelector('i');
        if (isValid) {
          element.classList.add('valid');
          if (icon) {
            icon.className = 'bi bi-check-circle-fill text-success';
          }
        } else {
          element.classList.remove('valid');
          if (icon) {
            icon.className = 'bi bi-dash-circle text-muted';
          }
        }
      }

      // 1. Length >= 8
      updateRule(passwordRules.length, val.length >= 8);

      // 2. Uppercase & Lowercase
      updateRule(passwordRules.cases, /[A-Z]/.test(val) && /[a-z]/.test(val));

      // 3. Numbers
      updateRule(passwordRules.number, /[0-9]/.test(val));

      // 4. Special Characters
      updateRule(passwordRules.symbol, /[@$!%*#?&]/.test(val));
    });
  }
});
