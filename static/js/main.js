/* ============================================
   ReconcileHub - Enhanced JavaScript
   UI Interactions & Animations v2.0
   ============================================ */

(function() {
    'use strict';

    // ============================================
    // Configuration
    // ============================================
    const CONFIG = {
        notificationCheckInterval: 30000, // 30 seconds
        toastDuration: 10000, // 10 seconds
        animationDuration: 300,
        debounceDelay: 250
    };

    // ============================================
    // Utility Functions
    // ============================================
    const Utils = {
        // Debounce function
        debounce(func, wait) {
            let timeout;
            return function executedFunction(...args) {
                const later = () => {
                    clearTimeout(timeout);
                    func(...args);
                };
                clearTimeout(timeout);
                timeout = setTimeout(later, wait);
            };
        },

        // Format date/time
        formatDateTime(date) {
            return new Intl.DateTimeFormat('en-US', {
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            }).format(new Date(date));
        },

        // Generate unique ID
        generateId() {
            return '_' + Math.random().toString(36).substr(2, 9);
        },

        // Check if element is in viewport
        isInViewport(element) {
            const rect = element.getBoundingClientRect();
            return (
                rect.top >= 0 &&
                rect.left >= 0 &&
                rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
                rect.right <= (window.innerWidth || document.documentElement.clientWidth)
            );
        }
    };

    // ============================================
    // DOM Ready Handler
    // ============================================
    document.addEventListener('DOMContentLoaded', function() {
        initializeApp();
    });

    function initializeApp() {
        // Initialize all modules
        SidebarManager.init();
        CardAnimations.init();
        TableEnhancements.init();
        FormEnhancements.init();
        TooltipManager.init();
        ScrollEffects.init();
        NotificationEnhancements.init();
        LoadingStates.init();
        
        // Add global animations
        addPageLoadAnimations();
        
        console.log('🚀 ReconcileHub UI Enhanced');
    }

    // ============================================
    // Sidebar Manager
    // ============================================
    const SidebarManager = {
        init() {
            this.sidebar = document.querySelector('.sidebar');
            this.mainContent = document.querySelector('.main-wrapper, .main-content');
            
            if (!this.sidebar) return;
            
            this.setupMobileToggle();
            this.setupActiveState();
            this.setupHoverEffects();
        },

        setupMobileToggle() {
            // Create mobile toggle button if not exists
            if (window.innerWidth <= 992 && !document.querySelector('.mobile-menu-toggle')) {
                const toggleBtn = document.createElement('button');
                toggleBtn.className = 'mobile-menu-toggle btn btn-primary';
                toggleBtn.innerHTML = '<i class="bi bi-list"></i>';
                toggleBtn.style.cssText = `
                    position: fixed;
                    top: 16px;
                    left: 16px;
                    z-index: 1060;
                    width: 44px;
                    height: 44px;
                    border-radius: 12px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    box-shadow: 0 4px 15px rgba(99, 102, 241, 0.4);
                `;
                
                toggleBtn.addEventListener('click', () => this.toggleSidebar());
                document.body.appendChild(toggleBtn);
            }

            // Close sidebar on outside click (mobile)
            document.addEventListener('click', (e) => {
                if (window.innerWidth <= 992 && 
                    this.sidebar.classList.contains('show') &&
                    !this.sidebar.contains(e.target) &&
                    !e.target.classList.contains('mobile-menu-toggle')) {
                    this.closeSidebar();
                }
            });
        },

        toggleSidebar() {
            this.sidebar.classList.toggle('show');
            document.body.classList.toggle('sidebar-open');
        },

        closeSidebar() {
            this.sidebar.classList.remove('show');
            document.body.classList.remove('sidebar-open');
        },

        setupActiveState() {
            const navLinks = this.sidebar.querySelectorAll('.nav-link');
            const currentPath = window.location.pathname;
            
            navLinks.forEach(link => {
                const href = link.getAttribute('href');
                if (href && currentPath.includes(href) && href !== '/') {
                    link.classList.add('active');
                }
            });
        },

        setupHoverEffects() {
            const navLinks = this.sidebar.querySelectorAll('.nav-link');
            
            navLinks.forEach(link => {
                link.addEventListener('mouseenter', function() {
                    this.style.transform = 'translateX(4px)';
                });
                
                link.addEventListener('mouseleave', function() {
                    if (!this.classList.contains('active')) {
                        this.style.transform = 'translateX(0)';
                    }
                });
            });
        }
    };

    // ============================================
    // Card Animations
    // ============================================
    const CardAnimations = {
        init() {
            this.setupStatCards();
            this.setupCardHovers();
            this.setupCardCountUp();
        },

        setupStatCards() {
            const statCards = document.querySelectorAll('.stat-card');
            
            statCards.forEach((card, index) => {
                // Staggered entrance animation
                card.style.opacity = '0';
                card.style.transform = 'translateY(20px)';
                
                setTimeout(() => {
                    card.style.transition = 'all 0.5s ease';
                    card.style.opacity = '1';
                    card.style.transform = 'translateY(0)';
                }, 100 + (index * 100));
            });
        },

        setupCardHovers() {
            const cards = document.querySelectorAll('.card');
            
            cards.forEach(card => {
                card.addEventListener('mouseenter', function() {
                    this.style.transform = 'translateY(-4px)';
                });
                
                card.addEventListener('mouseleave', function() {
                    this.style.transform = 'translateY(0)';
                });
            });
        },

        setupCardCountUp() {
            const statValues = document.querySelectorAll('.stat-card h3');
            
            statValues.forEach(element => {
                const finalValue = parseInt(element.textContent) || 0;
                if (finalValue > 0) {
                    this.animateValue(element, 0, finalValue, 1000);
                }
            });
        },

        animateValue(element, start, end, duration) {
            const startTimestamp = performance.now();
            
            const step = (timestamp) => {
                const progress = Math.min((timestamp - startTimestamp) / duration, 1);
                const easeProgress = 1 - Math.pow(1 - progress, 3); // Ease out cubic
                element.textContent = Math.floor(easeProgress * (end - start) + start);
                
                if (progress < 1) {
                    requestAnimationFrame(step);
                }
            };
            
            requestAnimationFrame(step);
        }
    };

    // ============================================
    // Table Enhancements
    // ============================================
    const TableEnhancements = {
        init() {
            this.setupRowAnimations();
            this.setupRowClickable();
            this.setupSortable();
        },

        setupRowAnimations() {
            const tableRows = document.querySelectorAll('.table tbody tr');
            
            tableRows.forEach((row, index) => {
                row.style.opacity = '0';
                row.style.transform = 'translateX(-10px)';
                
                setTimeout(() => {
                    row.style.transition = 'all 0.3s ease';
                    row.style.opacity = '1';
                    row.style.transform = 'translateX(0)';
                }, 50 + (index * 30));
            });
        },

        setupRowClickable() {
            const tableRows = document.querySelectorAll('.table tbody tr');
            
            tableRows.forEach(row => {
                const viewLink = row.querySelector('a[title="View"], a[href*="view"]');
                if (viewLink) {
                    row.style.cursor = 'pointer';
                    row.addEventListener('click', function(e) {
                        // Don't trigger if clicking on a button or link
                        if (e.target.closest('a, button')) return;
                        viewLink.click();
                    });
                }
            });
        },

        setupSortable() {
            // Add sort indicators to table headers
            const tableHeaders = document.querySelectorAll('.table thead th');
            
            tableHeaders.forEach(header => {
                if (!header.querySelector('a')) {
                    header.style.cursor = 'default';
                }
            });
        }
    };

    // ============================================
    // Form Enhancements
    // ============================================
    const FormEnhancements = {
        init() {
            this.setupFloatingLabels();
            this.setupValidation();
            this.setupAutoFocus();
            this.setupPasswordToggle();
        },

        setupFloatingLabels() {
            const formControls = document.querySelectorAll('.form-control');
            
            formControls.forEach(input => {
                input.addEventListener('focus', function() {
                    this.parentElement.classList.add('focused');
                });
                
                input.addEventListener('blur', function() {
                    if (!this.value) {
                        this.parentElement.classList.remove('focused');
                    }
                });
                
                // Check initial state
                if (input.value) {
                    input.parentElement.classList.add('focused');
                }
            });
        },

        setupValidation() {
            const forms = document.querySelectorAll('form');
            
            forms.forEach(form => {
                form.addEventListener('submit', function(e) {
                    const requiredInputs = this.querySelectorAll('[required]');
                    let isValid = true;
                    
                    requiredInputs.forEach(input => {
                        if (!input.value.trim()) {
                            isValid = false;
                            input.classList.add('is-invalid');
                            
                            // Add shake animation
                            input.style.animation = 'shake 0.5s ease';
                            setTimeout(() => {
                                input.style.animation = '';
                            }, 500);
                        } else {
                            input.classList.remove('is-invalid');
                        }
                    });
                    
                    if (!isValid) {
                        e.preventDefault();
                    }
                });
            });
        },

        setupAutoFocus() {
            const firstInput = document.querySelector('form .form-control:not([type="hidden"])');
            if (firstInput && !firstInput.value) {
                setTimeout(() => firstInput.focus(), 300);
            }
        },

        setupPasswordToggle() {
            const passwordInputs = document.querySelectorAll('input[type="password"]');
            
            passwordInputs.forEach(input => {
                const wrapper = document.createElement('div');
                wrapper.className = 'position-relative';
                input.parentNode.insertBefore(wrapper, input);
                wrapper.appendChild(input);
                
                const toggle = document.createElement('button');
                toggle.type = 'button';
                toggle.className = 'btn btn-link position-absolute';
                toggle.style.cssText = 'right: 10px; top: 50%; transform: translateY(-50%); color: var(--gray-400); z-index: 10;';
                toggle.innerHTML = '<i class="bi bi-eye"></i>';
                
                toggle.addEventListener('click', function() {
                    const type = input.getAttribute('type') === 'password' ? 'text' : 'password';
                    input.setAttribute('type', type);
                    this.innerHTML = type === 'password' ? '<i class="bi bi-eye"></i>' : '<i class="bi bi-eye-slash"></i>';
                });
                
                wrapper.appendChild(toggle);
            });
        }
    };

    // ============================================
    // Tooltip Manager
    // ============================================
    const TooltipManager = {
        init() {
            // Initialize Bootstrap tooltips
            const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"], [title]');
            
            tooltipTriggerList.forEach(element => {
                if (element.title && !element.getAttribute('data-bs-toggle')) {
                    element.setAttribute('data-bs-toggle', 'tooltip');
                    element.setAttribute('data-bs-placement', 'top');
                }
            });

            // Initialize Bootstrap tooltips if available
            if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
                tooltipTriggerList.forEach(element => {
                    new bootstrap.Tooltip(element);
                });
            }
        }
    };

    // ============================================
    // Scroll Effects
    // ============================================
    const ScrollEffects = {
        init() {
            this.setupScrollReveal();
            this.setupSmoothScroll();
            this.setupScrollToTop();
        },

        setupScrollReveal() {
            const observerOptions = {
                root: null,
                rootMargin: '0px',
                threshold: 0.1
            };
            
            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        entry.target.classList.add('revealed');
                        observer.unobserve(entry.target);
                    }
                });
            }, observerOptions);
            
            document.querySelectorAll('.card, .alert').forEach(element => {
                element.classList.add('reveal-on-scroll');
                observer.observe(element);
            });
        },

        setupSmoothScroll() {
            document.querySelectorAll('a[href^="#"]').forEach(anchor => {
                anchor.addEventListener('click', function(e) {
                    const target = document.querySelector(this.getAttribute('href'));
                    if (target) {
                        e.preventDefault();
                        target.scrollIntoView({
                            behavior: 'smooth',
                            block: 'start'
                        });
                    }
                });
            });
        },

        setupScrollToTop() {
            const scrollTopBtn = document.createElement('button');
            scrollTopBtn.className = 'scroll-to-top';
            scrollTopBtn.innerHTML = '<i class="bi bi-arrow-up"></i>';
            scrollTopBtn.style.cssText = `
                position: fixed;
                bottom: 30px;
                right: 30px;
                width: 48px;
                height: 48px;
                border-radius: 50%;
                background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
                color: white;
                border: none;
                cursor: pointer;
                opacity: 0;
                visibility: hidden;
                transition: all 0.3s ease;
                z-index: 1000;
                box-shadow: 0 4px 15px rgba(99, 102, 241, 0.4);
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 1.25rem;
            `;
            
            document.body.appendChild(scrollTopBtn);
            
            window.addEventListener('scroll', Utils.debounce(() => {
                if (window.pageYOffset > 300) {
                    scrollTopBtn.style.opacity = '1';
                    scrollTopBtn.style.visibility = 'visible';
                } else {
                    scrollTopBtn.style.opacity = '0';
                    scrollTopBtn.style.visibility = 'hidden';
                }
            }, 100));
            
            scrollTopBtn.addEventListener('click', () => {
                window.scrollTo({
                    top: 0,
                    behavior: 'smooth'
                });
            });
        }
    };

    // ============================================
    // Notification Enhancements
    // ============================================
    const NotificationEnhancements = {
        init() {
            this.setupNotificationSounds();
            this.enhanceNotificationDropdown();
        },

        setupNotificationSounds() {
            // Create notification sound (optional, commented by default)
            // const audio = new Audio('data:audio/wav;base64,...');
            
            // Override the showToast function if it exists
            if (typeof window.showToast === 'function') {
                const originalShowToast = window.showToast;
                window.showToast = function(notif) {
                    // audio.play(); // Uncomment to enable sound
                    originalShowToast(notif);
                };
            }
        },

        enhanceNotificationDropdown() {
            const dropdown = document.getElementById('notificationDropdown');
            if (!dropdown) return;
            
            // Add keyboard navigation
            dropdown.addEventListener('keydown', (e) => {
                const items = dropdown.querySelectorAll('.notification-item');
                const currentIndex = Array.from(items).findIndex(item => item === document.activeElement);
                
                if (e.key === 'ArrowDown') {
                    e.preventDefault();
                    const nextIndex = (currentIndex + 1) % items.length;
                    items[nextIndex]?.focus();
                } else if (e.key === 'ArrowUp') {
                    e.preventDefault();
                    const prevIndex = currentIndex <= 0 ? items.length - 1 : currentIndex - 1;
                    items[prevIndex]?.focus();
                } else if (e.key === 'Escape') {
                    dropdown.classList.remove('show');
                }
            });
        }
    };

    // ============================================
    // Loading States
    // ============================================
    const LoadingStates = {
        init() {
            this.setupButtonLoading();
            this.setupLinkLoading();
        },

        setupButtonLoading() {
            document.querySelectorAll('form').forEach(form => {
                form.addEventListener('submit', function() {
                    const submitBtn = this.querySelector('button[type="submit"]');
                    if (submitBtn) {
                        const originalText = submitBtn.innerHTML;
                        submitBtn.disabled = true;
                        submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Processing...';
                        
                        // Reset after timeout (fallback)
                        setTimeout(() => {
                            submitBtn.disabled = false;
                            submitBtn.innerHTML = originalText;
                        }, 10000);
                    }
                });
            });
        },

        setupLinkLoading() {
            // Add loading indicator for navigation
            document.querySelectorAll('a:not([href^="#"]):not([target="_blank"])').forEach(link => {
                link.addEventListener('click', function(e) {
                    if (this.href && !this.href.includes('#')) {
                        document.body.classList.add('page-loading');
                    }
                });
            });
        }
    };

    // ============================================
    // Page Load Animations
    // ============================================
    function addPageLoadAnimations() {
        // Add CSS for animations
        const style = document.createElement('style');
        style.textContent = `
            /* Shake animation for validation */
            @keyframes shake {
                0%, 100% { transform: translateX(0); }
                10%, 30%, 50%, 70%, 90% { transform: translateX(-5px); }
                20%, 40%, 60%, 80% { transform: translateX(5px); }
            }
            
            /* Reveal animation */
            .reveal-on-scroll {
                opacity: 0;
                transform: translateY(20px);
                transition: all 0.6s ease;
            }
            
            .reveal-on-scroll.revealed {
                opacity: 1;
                transform: translateY(0);
            }
            
            /* Page loading overlay */
            .page-loading::after {
                content: '';
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(255, 255, 255, 0.8);
                z-index: 9999;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            
            /* Pulse animation for badges */
            @keyframes pulse-badge {
                0%, 100% { transform: scale(1); }
                50% { transform: scale(1.1); }
            }
            
            /* Smooth hover transitions */
            .btn, .card, .nav-link, .table tbody tr {
                transition: all 0.2s ease !important;
            }
            
            /* Focus styles */
            *:focus-visible {
                outline: 2px solid var(--primary) !important;
                outline-offset: 2px !important;
            }
            
            /* Loading spinner in buttons */
            .spinner-border-sm {
                width: 1rem;
                height: 1rem;
                border-width: 0.15rem;
            }
        `;
        document.head.appendChild(style);
        
        // Add page entrance animation
        const mainContent = document.querySelector('.main-content');
        if (mainContent) {
            mainContent.style.opacity = '0';
            mainContent.style.transform = 'translateY(10px)';
            
            setTimeout(() => {
                mainContent.style.transition = 'all 0.5s ease';
                mainContent.style.opacity = '1';
                mainContent.style.transform = 'translateY(0)';
            }, 100);
        }
    }

    // ============================================
    // Global Exports
    // ============================================
    window.ReconcileHub = {
        Utils,
        SidebarManager,
        CardAnimations,
        TableEnhancements,
        FormEnhancements,
        TooltipManager,
        ScrollEffects,
        NotificationEnhancements,
        LoadingStates,
        
        // Utility methods
        showLoading() {
            document.body.classList.add('page-loading');
        },
        
        hideLoading() {
            document.body.classList.remove('page-loading');
        },
        
        showSuccess(message) {
            this.showAlert(message, 'success');
        },
        
        showError(message) {
            this.showAlert(message, 'danger');
        },
        
        showAlert(message, type = 'info') {
            const alertContainer = document.querySelector('.main-content') || document.body;
            const alert = document.createElement('div');
            alert.className = `alert alert-${type} alert-dismissible fade show`;
            alert.style.animation = 'slideDown 0.3s ease';
            alert.innerHTML = `
                <i class="bi bi-${type === 'success' ? 'check-circle' : type === 'danger' ? 'exclamation-triangle' : 'info-circle'}-fill me-2"></i>
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `;
            
            alertContainer.insertBefore(alert, alertContainer.firstChild);
            
            // Auto dismiss
            setTimeout(() => {
                alert.classList.remove('show');
                setTimeout(() => alert.remove(), 300);
            }, 5000);
        }
    };

})();
