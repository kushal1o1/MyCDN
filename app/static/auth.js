// Initialize Lucide icons
lucide.createIcons();

// Handle login form submission
document.getElementById('login-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    const captchaText = document.getElementById('captcha').value;
    const errorMessage = document.getElementById('error-message');
    
    // Hide any previous error
    errorMessage.classList.remove('show');
    
    const formData = new FormData();
    formData.append('captcha_text', captchaText);

    try {
        const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: {
                'Authorization': `Basic ${btoa(`${username}:${password}`)}`
            },
            body: formData
        });

        if (response.ok) {
            window.location.href = '/dashboard';
        } else {
            const errorData = await response.json();
            const errorSpan = errorMessage.querySelector('span');
            errorSpan.textContent = errorData.detail || 'Invalid username or password';
            errorMessage.classList.add('show');
            // Refresh captcha on failed login
            document.getElementById('captcha-image').src = '/api/captcha?' + new Date().getTime();
        }
    } catch (error) {
        const errorSpan = errorMessage.querySelector('span');
        errorSpan.textContent = 'An error occurred. Please try again.';
        errorMessage.classList.add('show');
    }
});

document.getElementById('refresh-captcha').addEventListener('click', () => {
    // Append a timestamp to prevent browser caching of the image
    document.getElementById('captcha-image').src = '/api/captcha?' + new Date().getTime();
}); 