// --- Navigation & UI Logic ---

        // Sticky Header Effect
        const header = document.getElementById('main-header');
        window.addEventListener('scroll', () => {
            if (window.scrollY > 50) {
                header.classList.add('py-0', 'bg-brand-dark/95', 'shadow-lg');
                header.classList.remove('bg-brand-dark/85');
            } else {
                header.classList.remove('py-0', 'bg-brand-dark/95', 'shadow-lg');
                header.classList.add('bg-brand-dark/85');
            }
        });

        // Mobile Menu Toggle
        function toggleMenu() {
            const menu = document.getElementById('mobile-menu');
            const overlay = document.getElementById('mobile-menu-overlay');
            const isOpen = !menu.classList.contains('translate-x-full');

            if (isOpen) {
                menu.classList.add('translate-x-full');
                overlay.classList.add('hidden');
                document.body.style.overflow = '';
            } else {
                menu.classList.remove('translate-x-full');
                overlay.classList.remove('hidden');
                document.body.style.overflow = 'hidden';
            }
        }

        // Mobile Submenu Toggle
        function toggleSubmenu(id) {
            const submenu = document.getElementById(id);
            const isHidden = submenu.classList.contains('hidden');
            const btn = submenu.previousElementSibling.querySelector('button i');

            if (isHidden) {
                submenu.classList.remove('hidden');
                btn.classList.remove('fa-plus');
                btn.classList.add('fa-minus');
            } else {
                submenu.classList.add('hidden');
                btn.classList.remove('fa-minus');
                btn.classList.add('fa-plus');
            }
        }

        // Modal Logic
        function openModal() {
            const modal = document.getElementById('consultModal');
            modal.classList.remove('hidden');
            // Reset form state on open
            document.getElementById('modalFormSuccess').classList.add('hidden');
            document.getElementById('modalForm').reset();
            document.body.style.overflow = 'hidden';
        }

        function closeModal() {
            document.getElementById('consultModal').classList.add('hidden');
            document.body.style.overflow = '';
        }

        // --- Form Handling (Simulation) ---
        function handleFormSubmit(e, formId) {
            e.preventDefault();
            const btn = e.target.querySelector('button[type="submit"]');
            const originalText = btn.innerText;
            const successMsg = document.getElementById(formId + 'Success');

            // Simulate Loading
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Sending...';
            btn.disabled = true;

            setTimeout(() => {
                btn.innerHTML = originalText;
                btn.disabled = false;
                successMsg.classList.remove('hidden');
                e.target.reset();

                // Hide success message after 3 seconds
                setTimeout(() => {
                    successMsg.classList.add('hidden');
                    if(formId === 'modalForm') closeModal();
                }, 3000);
            }, 1500);
        }

        // --- Slider Logic ---
        let currentSlide = 0;
        const slides = document.querySelectorAll('#hero-slider img');

        function nextSlide() {
            slides[currentSlide].style.opacity = '0';
            currentSlide = (currentSlide + 1) % slides.length;
            slides[currentSlide].style.opacity = '1';
        }

        setInterval(nextSlide, 4000);

        // --- Scroll Reveal Animation ---
        const observerOptions = {
            threshold: 0.1,
            rootMargin: "0px 0px -50px 0px"
        };

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('active');
                    observer.unobserve(entry.target); // Only animate once
                }
            });
        }, observerOptions);

        document.querySelectorAll('.reveal').forEach(el => observer.observe(el));