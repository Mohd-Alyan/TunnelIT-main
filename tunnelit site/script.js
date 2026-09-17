document.addEventListener('DOMContentLoaded', () => {
    // Determine the actual domain this site is hosted on
    // Fallback to a clear placeholder if opened locally as file://
    const isLocalFile = window.location.protocol === 'file:';
    const siteDomain = isLocalFile ? 'tunnelit.example.com' : window.location.host;
    
    // Update the domain in the installation command text
    const domainSpans = document.querySelectorAll('.site-domain');
    domainSpans.forEach(span => {
        span.textContent = siteDomain;
    });

    // Copy to clipboard functionality
    const copyBtn = document.getElementById('copy-install-btn');
    if (copyBtn) {
        copyBtn.addEventListener('click', async () => {
            const command = `irm https://${siteDomain}/install.ps1 | iex`;
            
            try {
                await navigator.clipboard.writeText(command);
                
                // Show feedback
                const originalText = copyBtn.textContent;
                copyBtn.textContent = 'Copied';
                copyBtn.style.color = '#fff';
                copyBtn.style.borderColor = '#3b82f6';
                copyBtn.style.backgroundColor = '#3b82f6';
                
                setTimeout(() => {
                    copyBtn.textContent = originalText;
                    copyBtn.style.color = '';
                    copyBtn.style.borderColor = '';
                    copyBtn.style.backgroundColor = '';
                }, 2000);
            } catch (err) {
                console.error('Failed to copy text: ', err);
                copyBtn.textContent = 'Error';
                setTimeout(() => {
                    copyBtn.textContent = 'Copy';
                }, 2000);
            }
        });
    }

    // Smooth scrolling for navigation links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            const targetId = this.getAttribute('href');
            if (targetId === '#') return;
            
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
