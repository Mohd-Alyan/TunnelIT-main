document.addEventListener('DOMContentLoaded', () => {
    // Determine the actual domain this site is hosted on
    const isLocalFile = window.location.protocol === 'file:';
    const siteDomain = isLocalFile ? 'tunnel-it.vercel.app' : window.location.host;
    
    // Update the domain in the installation command text
    const domainSpans = document.querySelectorAll('.site-domain');
    domainSpans.forEach(span => {
        span.textContent = siteDomain;
    });

    // Copy to clipboard functionality - Main Install Button
    const copyInstallBtn = document.getElementById('copy-install-btn');
    if (copyInstallBtn) {
        copyInstallBtn.addEventListener('click', async () => {
            const command = `irm https://${siteDomain}/install.ps1 | iex`;
            const icon = copyInstallBtn.querySelector('i');
            
            try {
                await navigator.clipboard.writeText(command);
                const origText = copyInstallBtn.innerHTML;
                copyInstallBtn.innerHTML = '<i class="ph-bold ph-check"></i> COPIED';
                
                setTimeout(() => {
                    copyInstallBtn.innerHTML = origText;
                }, 2000);
            } catch (err) {
                console.error('Failed to copy text: ', err);
            }
        });
    }
    
    // Quick Start Copy Buttons
    const quickStartCopyBtns = document.querySelectorAll('.copy-icon-btn');
    quickStartCopyBtns.forEach(btn => {
        btn.addEventListener('click', async () => {
            const codeBlock = btn.previousElementSibling;
            if (!codeBlock) return;
            
            let commandToCopy = codeBlock.textContent;
            if (codeBlock.querySelector('.site-domain')) {
                commandToCopy = `irm https://${siteDomain}/install.ps1 | iex`;
            }
            
            const icon = btn.querySelector('i');
            
            try {
                await navigator.clipboard.writeText(commandToCopy);
                
                if (icon) {
                    icon.classList.remove('ph-copy');
                    icon.classList.add('ph-check', 'text-success');
                }
                
                setTimeout(() => {
                    if (icon) {
                        icon.classList.remove('ph-check', 'text-success');
                        icon.classList.add('ph-copy');
                    }
                }, 2000);
            } catch (err) {
                console.error('Failed to copy text: ', err);
            }
        });
    });
    
    // Smooth scrolling for internal links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            const targetId = this.getAttribute('href');
            if (targetId === '#' || targetId === '#!') return;
            
            const targetElement = document.querySelector(targetId);
            if (targetElement) {
                e.preventDefault();
                targetElement.scrollIntoView({
                    behavior: 'smooth'
                });
            }
        });
    });
});
