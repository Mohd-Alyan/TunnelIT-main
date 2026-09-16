document.addEventListener('DOMContentLoaded', () => {
    const mainText = document.getElementById('main-text');
    
    // Add a simple interaction just to utilize JS as requested
    mainText.addEventListener('click', () => {
        // Quick visual feedback on click
        mainText.style.transform = 'scale(0.9)';
        setTimeout(() => {
            mainText.style.transform = ''; // Reset to let CSS handle hover state
        }, 150);
    });
});
