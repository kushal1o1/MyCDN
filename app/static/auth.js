// Initialize Lucide icons
lucide.createIcons();

// Handle login form submission
document.getElementById('login-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    const errorMessage = document.getElementById('error-message');
    
    // Hide any previous error
    errorMessage.classList.remove('show');
    
    try {
        const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: {
                'Authorization': `Basic ${btoa(`${username}:${password}`)}`
            }
        });

        if (response.ok) {
            window.location.href = '/dashboard';
        } else {
            const errorSpan = errorMessage.querySelector('span');
            errorSpan.textContent = 'Invalid username or password';
            errorMessage.classList.add('show');
        }
    } catch (error) {
        const errorSpan = errorMessage.querySelector('span');
        errorSpan.textContent = 'An error occurred. Please try again.';
        errorMessage.classList.add('show');
    }
}); 