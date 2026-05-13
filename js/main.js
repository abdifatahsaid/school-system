/* ═══════════════════════════════════
   SCHOOL MANAGEMENT SYSTEM
   Created By Abdifatah Said
   ═══════════════════════════════════ */

// ── SIDEBAR TOGGLE ──
const sidebar = document.getElementById('sidebar');
const mainContent = document.getElementById('mainContent');
const menuToggle = document.getElementById('menuToggle');

if (menuToggle) {
    menuToggle.addEventListener('click', () => {
        if (window.innerWidth <= 768) {
            sidebar.classList.toggle('mobile-open');
        } else {
            sidebar.classList.toggle('collapsed');
            mainContent.classList.toggle('expanded');
        }
    });
}

// Close sidebar on mobile when clicking outside
document.addEventListener('click', (e) => {
    if (window.innerWidth <= 768) {
        if (!sidebar.contains(e.target) && !menuToggle.contains(e.target)) {
            sidebar.classList.remove('mobile-open');
        }
    }
});

// ── ROLE BUTTONS (LOGIN) ──
const roleBtns = document.querySelectorAll('.role-btn');
const roleInput = document.getElementById('roleInput');

roleBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        roleBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        if (roleInput) roleInput.value = btn.dataset.role;

        // Update placeholder
        const usernameInput = document.getElementById('username');
        if (usernameInput) {
            usernameInput.placeholder = btn.dataset.role === 'student'
                ? 'Enter your Student ID'
                : 'Enter username';
        }
    });
});

// ── LOGIN BUTTON ANIMATION ──
const loginBtn = document.getElementById('loginBtn');
if (loginBtn) {
    loginBtn.addEventListener('click', function () {
        const original = this.innerHTML;
        this.innerHTML = '<span class="spinner"></span> Logging in...';
        this.disabled = true;
        setTimeout(() => {
            this.innerHTML = original;
            this.disabled = false;
        }, 3000);
    });
}

// ── ACTIVE NAV ITEM ──
const navItems = document.querySelectorAll('.nav-item');
navItems.forEach(item => {
    item.addEventListener('click', () => {
        navItems.forEach(i => i.classList.remove('active'));
        item.classList.add('active');
    });
});

// ── SEARCH FUNCTION ──
function searchTable(inputId, tableId) {
    const input = document.getElementById(inputId);
    const table = document.getElementById(tableId);

    if (!input || !table) return;

    input.addEventListener('keyup', () => {
        const filter = input.value.toLowerCase();
        const rows = table.querySelectorAll('tbody tr');

        rows.forEach(row => {
            const text = row.textContent.toLowerCase();
            row.style.display = text.includes(filter) ? '' : 'none';
        });
    });
}

// Initialize search
searchTable('searchInput', 'studentsTable');
searchTable('searchInput', 'feesTable');
searchTable('searchInput', 'gradesTable');
searchTable('searchInput', 'attendanceTable');

// ── MODAL ──
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
        setTimeout(() => modal.classList.add('show'), 10);
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('show');
        document.body.style.overflow = '';
        setTimeout(() => modal.style.display = 'none', 300);
    }
}

// Close modal on overlay click
document.querySelectorAll('.modal-overlay').forEach(overlay => {
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) {
            overlay.style.display = 'none';
            document.body.style.overflow = '';
        }
    });
});

// ── ALERTS ──
function showAlert(message, type = 'success', duration = 3000) {
    const alert = document.createElement('div');
    alert.className = `alert alert-${type}`;
    alert.innerHTML = `
        <span>${type === 'success' ? '✅' : type === 'error' ? '❌' : '⚠️'}</span>
        <span>${message}</span>
    `;

    const container = document.getElementById('alertContainer');
    if (container) {
        container.appendChild(alert);
        setTimeout(() => {
            alert.style.opacity = '0';
            alert.style.transform = 'translateY(-10px)';
            alert.style.transition = 'all 0.3s ease';
            setTimeout(() => alert.remove(), 300);
        }, duration);
    }
}

// ── PROGRESS BARS ANIMATION ──
function animateProgressBars() {
    document.querySelectorAll('.progress-fill').forEach(bar => {
        const width = bar.dataset.width || '0';
        bar.style.width = '0%';
        setTimeout(() => {
            bar.style.width = width + '%';
        }, 300);
    });
}

// ── PROFILE PHOTO UPLOAD ──
function initPhotoUpload() {
    const photoInput = document.getElementById('photoInput');
    const profilePhoto = document.getElementById('profilePhoto');

    if (photoInput && profilePhoto) {
        profilePhoto.addEventListener('click', () => photoInput.click());

        photoInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = (e) => {
                    profilePhoto.src = e.target.result;

                    // Upload to server
                    const formData = new FormData();
                    formData.append('photo', file);

                    fetch('/upload_photo', {
                        method: 'POST',
                        body: formData
                    })
                    .then(res => res.json())
                    .then(data => {
                        if (data.success) {
                            showAlert('Photo updated successfully!', 'success');
                        } else {
                            showAlert('Failed to update photo!', 'error');
                        }
                    })
                    .catch(() => showAlert('Error uploading photo!', 'error'));
                };
                reader.readAsDataURL(file);
            }
        });
    }
}

// ── VOTE FUNCTION ──
function initVoting() {
    const voteCards = document.querySelectorAll('.vote-card');
    voteCards.forEach(card => {
        const voteBtn = card.querySelector('.vote-btn');
        if (voteBtn && !voteBtn.disabled) {
            voteBtn.addEventListener('click', () => {
                const candidateId = card.dataset.candidateId;

                // Confirm vote
                if (confirm(`Are you sure you want to vote for ${card.querySelector('h3').textContent}?`)) {
                    fetch('/submit_vote', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ candidate_id: candidateId })
                    })
                    .then(res => res.json())
                    .then(data => {
                        if (data.success) {
                            showAlert('Vote submitted successfully! 🎉', 'success');
                            setTimeout(() => location.reload(), 1500);
                        } else {
                            showAlert(data.message || 'Failed to submit vote!', 'error');
                        }
                    })
                    .catch(() => showAlert('Error submitting vote!', 'error'));
                }
            });
        }
    });
}

// ── ATTENDANCE CHECKBOXES ──
function initAttendance() {
    const selectAllPresent = document.getElementById('selectAllPresent');
    const selectAllAbsent = document.getElementById('selectAllAbsent');

    if (selectAllPresent) {
        selectAllPresent.addEventListener('click', () => {
            document.querySelectorAll('.status-present').forEach(cb => cb.checked = true);
            document.querySelectorAll('.status-absent').forEach(cb => cb.checked = false);
        });
    }

    if (selectAllAbsent) {
        selectAllAbsent.addEventListener('click', () => {
            document.querySelectorAll('.status-absent').forEach(cb => cb.checked = true);
            document.querySelectorAll('.status-present').forEach(cb => cb.checked = false);
        });
    }
}

// ── NUMBER COUNTER ANIMATION ──
function animateCounters() {
    document.querySelectorAll('.stat-number').forEach(counter => {
        const target = parseInt(counter.dataset.target || counter.textContent);
        const duration = 1500;
        const step = target / (duration / 16);
        let current = 0;

        const timer = setInterval(() => {
            current += step;
            if (current >= target) {
                counter.textContent = target;
                clearInterval(timer);
            } else {
                counter.textContent = Math.floor(current);
            }
        }, 16);
    });
}

// ── GRADE COLOR ──
function getGradeClass(score) {
    if (score >= 80) return 'grade-a';
    if (score >= 70) return 'grade-b';
    if (score >= 60) return 'grade-c';
    if (score >= 50) return 'grade-d';
    return 'grade-f';
}

function getGradeLetter(score) {
    if (score >= 80) return 'A';
    if (score >= 70) return 'B';
    if (score >= 60) return 'C';
    if (score >= 50) return 'D';
    return 'F';
}

// ── CONFIRM DELETE ──
function confirmDelete(studentId, studentName) {
    if (confirm(`Are you sure you want to delete ${studentName}?\nThis action cannot be undone!`)) {
        fetch('/delete_student', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ student_id: studentId })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                showAlert(`${studentName} deleted successfully!`, 'success');
                setTimeout(() => location.reload(), 1500);
            } else {
                showAlert('Failed to delete student!', 'error');
            }
        })
        .catch(() => showAlert('Error deleting student!', 'error'));
    }
}

// ── INITIALIZE ──
document.addEventListener('DOMContentLoaded', () => {
    animateProgressBars();
    animateCounters();
    initPhotoUpload();
    initVoting();
    initAttendance();

    // Add alert container
    if (!document.getElementById('alertContainer')) {
        const container = document.createElement('div');
        container.id = 'alertContainer';
        container.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
            display: flex;
            flex-direction: column;
            gap: 10px;
            max-width: 350px;
        `;
        document.body.appendChild(container);
    }

    console.log('🎓 School Management System Loaded!');
});