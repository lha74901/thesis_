// employee_predictor/static/employee_predictor/js/main.js

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            document.querySelector(this.getAttribute('href')).scrollIntoView({
                behavior: 'smooth'
            });
        });
    });

    // Table row highlighting
    const highlightTableRow = () => {
        document.querySelectorAll('.table tbody tr').forEach(row => {
            row.addEventListener('mouseenter', () => {
                row.style.transition = 'all 0.3s ease';
                row.style.transform = 'scale(1.01)';
            });
            row.addEventListener('mouseleave', () => {
                row.style.transform = 'scale(1)';
            });
        });
    };

    // Form validation enhancement
    const enhanceFormValidation = () => {
        const forms = document.querySelectorAll('.needs-validation');
        forms.forEach(form => {
            form.addEventListener('submit', event => {
                if (!form.checkValidity()) {
                    event.preventDefault();
                    event.stopPropagation();
                }
                form.classList.add('was-validated');
            });
        });
    };

    // Dynamic search filtering
    const setupDynamicSearch = () => {
        const searchInput = document.querySelector('#tableSearch');
        if (searchInput) {
            searchInput.addEventListener('keyup', function() {
                const searchTerm = this.value.toLowerCase();
                const table = document.querySelector('.table');
                const rows = table.querySelectorAll('tbody tr');

                rows.forEach(row => {
                    const text = row.textContent.toLowerCase();
                    row.style.display = text.includes(searchTerm) ? '' : 'none';
                });
            });
        }
    };

    // Card animation on scroll
    const animateCardsOnScroll = () => {
        const cards = document.querySelectorAll('.card');
        const observer = new IntersectionObserver(entries => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.style.opacity = '1';
                    entry.target.style.transform = 'translateY(0)';
                }
            });
        });

        cards.forEach(card => {
            card.style.opacity = '0';
            card.style.transform = 'translateY(20px)';
            card.style.transition = 'all 0.5s ease-out';
            observer.observe(card);
        });
    };

    // Chart animations
    const animateCharts = () => {
        const charts = document.querySelectorAll('.chart-animation');
        charts.forEach(chart => {
            chart.style.transition = 'all 1s ease';
            chart.style.transform = 'scale(1)';
            chart.style.opacity = '1';
        });
    };

    // Form input animation
    const setupFormInputEffects = () => {
        const formControls = document.querySelectorAll('.form-control');
        formControls.forEach(input => {
            input.addEventListener('focus', () => {
                input.parentElement.classList.add('focused');
            });
            input.addEventListener('blur', () => {
                if (!input.value) {
                    input.parentElement.classList.remove('focused');
                }
            });
        });
    };

    // Notification system
    const setupNotifications = () => {
        const notifications = document.querySelectorAll('.alert');
        notifications.forEach(notification => {
            setTimeout(() => {
                notification.style.transition = 'all 0.5s ease';
                notification.style.opacity = '0';
                setTimeout(() => {
                    notification.remove();
                }, 500);
            }, 5000);
        });
    };

    // Date range picker initialization
    const initializeDateRangePicker = () => {
        const dateRangePickers = document.querySelectorAll('.date-range-picker');
        dateRangePickers.forEach(picker => {
            if (typeof daterangepicker !== 'undefined') {
                $(picker).daterangepicker({
                    opens: 'left',
                    autoUpdateInput: false,
                    locale: {
                        cancelLabel: 'Clear'
                    }
                });

                $(picker).on('apply.daterangepicker', function(ev, picker) {
                    $(this).val(picker.startDate.format('MM/DD/YYYY') + ' - ' + picker.endDate.format('MM/DD/YYYY'));
                });

                $(picker).on('cancel.daterangepicker', function(ev, picker) {
                    $(this).val('');
                });
            }
        });
    };

    // Progress bar animation
    const animateProgressBars = () => {
        const progressBars = document.querySelectorAll('.progress-bar');
        progressBars.forEach(bar => {
            const targetWidth = bar.getAttribute('aria-valuenow') + '%';
            bar.style.transition = 'width 1s ease';
            bar.style.width = targetWidth;
        });
    };

    // Initialize all animations and enhancements
    highlightTableRow();
    enhanceFormValidation();
    setupDynamicSearch();
    animateCardsOnScroll();
    animateCharts();
    setupFormInputEffects();
    setupNotifications();
    initializeDateRangePicker();
    animateProgressBars();

    // Handle loading states
        // Handle loading states
    const handleLoadingStates = () => {
        const buttons = document.querySelectorAll('.btn-loading');
        buttons.forEach(button => {
            button.addEventListener('click', () => {
                button.disabled = true;
                const originalText = button.textContent;
                button.innerHTML = `
                    <span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                    Loading...
                `;
                setTimeout(() => {
                    button.disabled = false;
                    button.textContent = originalText;
                }, 2000);
            });
        });
    };

    // Data table enhancements
    const enhanceDataTables = () => {
        const tables = document.querySelectorAll('.datatable');
        tables.forEach(table => {
            $(table).DataTable({
                responsive: true,
                pageLength: 10,
                dom: 'Bfrtip',
                buttons: [
                    'copy', 'excel', 'pdf', 'print'
                ]
            });
        });
    };

    // Sticky header
    const initializeStickyHeader = () => {
        const header = document.querySelector('.sticky-header');
        if (header) {
            const sticky = header.offsetTop;
            window.onscroll = () => {
                if (window.pageYOffset > sticky) {
                    header.classList.add('sticky');
                } else {
                    header.classList.remove('sticky');
                }
            };
        }
    };

    // Initialize all enhancements
    handleLoadingStates();
    enhanceDataTables();
    initializeStickyHeader();
});