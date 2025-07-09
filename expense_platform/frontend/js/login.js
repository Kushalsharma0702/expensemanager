document.addEventListener('DOMContentLoaded', function() {
    const loginForm = document.getElementById('loginForm');
    const messageDiv = document.getElementById('message');
    
    loginForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const formData = new FormData(loginForm);
        const data = {
            email: formData.get('email'),
            password: formData.get('password')
        };
        
        try {
            const response = await fetch('/auth/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data),
                credentials: 'include'
            });
            
            const result = await response.json();
            
            if (response.ok) {
                showMessage('Login successful! Redirecting...', 'success');
                
                // Redirect based on user role
                setTimeout(() => {
                    window.location.href = result.redirect_url;
                }, 1000);
            } else {
                showMessage(result.error || 'Login failed', 'error');
            }
        } catch (error) {
            console.error('Login error:', error);
            showMessage('An error occurred during login', 'error');
        }
    });
    
    function showMessage(message, type) {
        if (messageDiv) {
            messageDiv.className = `mb-4 p-4 rounded-lg ${
                type === 'success' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
            }`;
            messageDiv.textContent = message;
            
            // Clear message after 5 seconds
            setTimeout(() => {
                messageDiv.textContent = '';
                messageDiv.className = '';
            }, 5000);
        }
    }
});