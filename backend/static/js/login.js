document.addEventListener('DOMContentLoaded', async function() {
    // Check if user is already logged in
    try {
        const response = await fetch('/auth/check-session', { credentials: 'include' });
        if (response.ok) {
            const result = await response.json();
            if (result.authenticated) {
                window.location.href = `/dashboard/${result.user.role}`;
                return;
            }
        }
    } catch (error) {
        // Not logged in, show login form
    }
    
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
                
                // Store user info in localStorage for session persistence
                localStorage.setItem('user_session', JSON.stringify({
                    id: result.user.id,
                    name: result.user.name,
                    email: result.user.email,
                    role: result.user.role,
                    login_time: new Date().toISOString()
                }));
                
                // Redirect to appropriate dashboard
                setTimeout(() => {
                    window.location.href = result.redirect_url;
                }, 1000);
            } else {
                showMessage(result.error || 'Login failed', 'error');
            }
        } catch (error) {
            console.error('Login error:', error);
            showMessage('Login failed. Please try again.', 'error');
        }
    });
    
    function showMessage(message, type) {
        if (messageDiv) {
            messageDiv.className = `p-4 mb-4 text-sm rounded-lg ${
                type === 'success' ? 'text-green-800 bg-green-50' : 'text-red-800 bg-red-50'
            }`;
            messageDiv.textContent = message;
            messageDiv.style.display = 'block';
            
            setTimeout(() => {
                messageDiv.style.display = 'none';
            }, 5000);
        }
    }
    
    document.getElementById('logoutBtn').addEventListener('click', async function() {
        await fetch('/auth/logout', { method: 'POST', credentials: 'include' });
        localStorage.clear();
        window.location.href = '/';
    });
});