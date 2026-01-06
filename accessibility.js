(function () {
    // --- Styles ---
    const styles = `
        #accessibility-toolbar-toggle {
            position: fixed;
            top: 50%;
            right: 0;
            transform: translateY(-50%);
            background: #D4AF37 !important;
            color: #121212 !important;
            width: 50px !important;
            height: 50px !important;
            border-radius: 8px 0 0 8px !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            cursor: pointer !important;
            z-index: 99999 !important;
            box-shadow: -2px 0 10px rgba(0,0,0,0.3) !important;
            transition: all 0.3s ease !important;
            border: none !important;
            visibility: visible !important;
            opacity: 1 !important;
        }
        #accessibility-toolbar-toggle:hover {
            width: 60px !important;
            background: #F3E5AB !important;
        }
        #accessibility-toolbar {
            position: fixed;
            top: 50%;
            right: -320px;
            transform: translateY(-50%);
            width: 300px !important;
            background: #1E1E1E !important;
            border: 1px solid #D4AF37 !important;
            border-radius: 12px 0 0 12px !important;
            padding: 24px !important;
            z-index: 100000 !important;
            box-shadow: -5px 0 20px rgba(0,0,0,0.5) !important;
            transition: right 0.4s cubic-bezier(0.4, 0, 0.2, 1) !important;
            color: #fff !important;
            font-family: 'Open Sans', sans-serif !important;
            font-size: 16px !important;
            visibility: visible !important;
            opacity: 1 !important;
        }
        #accessibility-toolbar.open {
            right: 0 !important;
        }
        .acc-header {
            display: flex !important;
            justify-content: space-between !important;
            align-items: center !important;
            margin-bottom: 20px !important;
            border-bottom: 1px solid rgba(212, 175, 55, 0.3) !important;
            padding-bottom: 12px !important;
            background: transparent !important;
        }
        .acc-header h3 {
            margin: 0 !important;
            font-size: 18px !important;
            color: #D4AF37 !important;
            font-family: 'Montserrat', sans-serif !important;
            text-transform: uppercase !important;
            letter-spacing: 1px !important;
            background: transparent !important;
        }
        .acc-close {
            cursor: pointer !important;
            color: #888 !important;
            transition: color 0.3s !important;
            font-size: 20px !important;
            background: transparent !important;
        }
        .acc-close:hover {
            color: #fff !important;
        }
        .acc-grid {
            display: grid !important;
            grid-template-columns: 1fr 1fr !important;
            gap: 12px !important;
            background: transparent !important;
        }
        .acc-btn {
            background: rgba(255,255,255,0.05) !important;
            border: 1px solid rgba(255,255,255,0.1) !important;
            color: #E0E0E0 !important;
            padding: 12px 8px !important;
            border-radius: 8px !important;
            cursor: pointer !important;
            display: flex !important;
            flex-direction: column !important;
            align-items: center !important;
            gap: 8px !important;
            transition: all 0.2s !important;
            font-size: 12px !important;
            text-align: center !important;
            font-family: 'Open Sans', sans-serif !important;
            line-height: 1.2 !important;
            width: auto !important;
            height: auto !important;
        }
        .acc-btn i {
            font-size: 20px !important;
            color: #D4AF37 !important;
            background: transparent !important;
        }
        .acc-btn:hover {
            background: rgba(212, 175, 55, 0.1) !important;
            border-color: #D4AF37 !important;
        }
        .acc-btn.active {
            background: #D4AF37 !important;
            color: #121212 !important;
            border-color: #D4AF37 !important;
        }
        .acc-btn.active i {
            color: #121212 !important;
        }
        .acc-btn-full {
            grid-column: span 2 !important;
        }
        
        /* Accessibility Overrides */
        body.acc-high-contrast *:not(.acc-ignore):not(.acc-ignore *) {
            background-color: #000 !important;
            color: #fff !important;
            border-color: #fff !important;
            box-shadow: none !important;
            text-shadow: none !important;
            background-image: none !important;
        }
        body.acc-high-contrast a:not(.acc-ignore):not(.acc-ignore *) {
            color: #ffff00 !important;
            text-decoration: underline !important;
        }
        
        /* Apply grayscale to children instead of body to avoid fixed positioning issue */
        body.acc-grayscale *:not(.acc-ignore):not(.acc-ignore *) {
            filter: grayscale(100%) !important;
        }
        
        body.acc-highlight-links a:not(.acc-ignore):not(.acc-ignore *) {
            outline: 3px solid #D4AF37 !important;
            background-color: rgba(212, 175, 55, 0.2) !important;
            color: #fff !important;
        }
        
        body.acc-readable-font *:not(.acc-ignore):not(.acc-ignore *) {
            font-family: Arial, Helvetica, sans-serif !important;
        }
    `;

    // --- Inject styles ---
    const styleSheet = document.createElement("style");
    styleSheet.innerText = styles;
    document.head.appendChild(styleSheet);

    // --- Create Toolbar HTML ---
    const toolbarToggle = document.createElement('div');
    toolbarToggle.id = 'accessibility-toolbar-toggle';
    toolbarToggle.className = 'acc-ignore';
    toolbarToggle.innerHTML = '<i class="fas fa-universal-access fa-2x"></i>';
    toolbarToggle.title = 'Accessibility Toolbar';

    const toolbar = document.createElement('div');
    toolbar.id = 'accessibility-toolbar';
    toolbar.className = 'acc-ignore';
    toolbar.innerHTML = `
        <div class="acc-header acc-ignore">
            <h3 class="acc-ignore">Accessibility</h3>
            <div class="acc-close acc-ignore"><i class="fas fa-times acc-ignore"></i></div>
        </div>
        <div class="acc-grid acc-ignore">
            <button type="button" class="acc-btn acc-ignore" id="acc-font-up">
                <i class="fas fa-font acc-ignore"></i>
                <span class="acc-ignore">Font Size +</span>
            </button>
            <button type="button" class="acc-btn acc-ignore" id="acc-font-down">
                <i class="fas fa-font acc-ignore" style="font-size: 14px;"></i>
                <span class="acc-ignore">Font Size -</span>
            </button>
            <button type="button" class="acc-btn acc-ignore" id="acc-contrast">
                <i class="fas fa-adjust acc-ignore"></i>
                <span class="acc-ignore">High Contrast</span>
            </button>
            <button type="button" class="acc-btn acc-ignore" id="acc-grayscale">
                <i class="fas fa-tint-slash acc-ignore"></i>
                <span class="acc-ignore">Grayscale</span>
            </button>
            <button type="button" class="acc-btn acc-ignore" id="acc-links">
                <i class="fas fa-link acc-ignore"></i>
                <span class="acc-ignore">Highlight Links</span>
            </button>
            <button type="button" class="acc-btn acc-ignore" id="acc-font-readable">
                <i class="fas fa-eye acc-ignore"></i>
                <span class="acc-ignore">Readable Font</span>
            </button>
            <button type="button" class="acc-btn acc-btn-full acc-ignore" id="acc-reset">
                <i class="fas fa-undo acc-ignore"></i>
                <span class="acc-ignore">Reset Settings</span>
            </button>
        </div>
    `;

    document.body.appendChild(toolbarToggle);
    document.body.appendChild(toolbar);

    // --- Logic ---
    let fontSize = 100;
    const body = document.body;

    const savedSettings = JSON.parse(localStorage.getItem('acc-settings') || '{}');

    function updateSettings() {
        const settings = {
            fontSize,
            contrast: body.classList.contains('acc-high-contrast'),
            grayscale: body.classList.contains('acc-grayscale'),
            links: body.classList.contains('acc-highlight-links'),
            readableFont: body.classList.contains('acc-readable-font')
        };
        localStorage.setItem('acc-settings', JSON.stringify(settings));

        // Update button states
        document.getElementById('acc-contrast').classList.toggle('active', settings.contrast);
        document.getElementById('acc-grayscale').classList.toggle('active', settings.grayscale);
        document.getElementById('acc-links').classList.toggle('active', settings.links);
        document.getElementById('acc-font-readable').classList.toggle('active', settings.readableFont);

        body.style.fontSize = fontSize + '%';
    }

    // Apply saved settings
    if (savedSettings.fontSize) fontSize = savedSettings.fontSize;
    if (savedSettings.contrast) body.classList.add('acc-high-contrast');
    if (savedSettings.grayscale) body.classList.add('acc-grayscale');
    if (savedSettings.links) body.classList.add('acc-highlight-links');
    if (savedSettings.readableFont) body.classList.add('acc-readable-font');
    updateSettings();

    // Event Listeners
    toolbarToggle.onclick = () => toolbar.classList.add('open');
    toolbar.querySelector('.acc-close').onclick = () => toolbar.classList.remove('open');

    document.getElementById('acc-font-up').onclick = () => {
        fontSize += 10;
        updateSettings();
    };
    document.getElementById('acc-font-down').onclick = () => {
        if (fontSize > 50) fontSize -= 10;
        updateSettings();
    };
    document.getElementById('acc-contrast').onclick = () => {
        body.classList.toggle('acc-high-contrast');
        updateSettings();
    };
    document.getElementById('acc-grayscale').onclick = () => {
        body.classList.toggle('acc-grayscale');
        updateSettings();
    };
    document.getElementById('acc-links').onclick = () => {
        body.classList.toggle('acc-highlight-links');
        updateSettings();
    };
    document.getElementById('acc-font-readable').onclick = () => {
        body.classList.toggle('acc-readable-font');
        updateSettings();
    };
    document.getElementById('acc-reset').onclick = () => {
        fontSize = 100;
        body.classList.remove('acc-high-contrast', 'acc-grayscale', 'acc-highlight-links', 'acc-readable-font');
        updateSettings();
    };

    // Close on escape
    window.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') toolbar.classList.remove('open');
    });

})();
