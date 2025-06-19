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
                'Content-Type': 'application/json',
                'Authorization': `Basic ${btoa(`${username}:${password}`)}`
            }
        });

        if (response.ok) {
            window.location.href = '/dashboard';
        } else {
            errorMessage.classList.add('show');
        }
    } catch (error) {
        errorMessage.classList.add('show');
    }
}); 