document.addEventListener('DOMContentLoaded', function() {
    loadUserInfo();
    loadAdmins();
    loadMyRequests();
    
    document.getElementById('expenseForm').addEventListener('submit', handleSubmitExpense);
    document.getElementById('logoutBtn').addEventListener('click', handleLogout);
});

async function loadUserInfo() {
    try {
        const response = await fetch('/auth/me', {
            credentials: 'include'
        });
        
        if (response.ok) {
            const user = await response.json();
            document.getElementById('userName').textContent = user.name;
        }
    } catch (error) {
        console.error('Error loading user info:', error);
    }
}

async function loadAdmins() {
    try {
        const response = await fetch('/employee/admins', {
            credentials: 'include'
        });
        
        if (response.ok) {
            const data = await response.json();
            const adminSelect = document.getElementById('adminSelect');
            
            data.admins.forEach(admin => {
                const option = document.createElement('option');
                option.value = admin.id;
                option.textContent = `${admin.name} (${admin.email})`;
                adminSelect.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Error loading admins:', error);
    }
}

async function loadMyRequests() {
    try {
        const response = await fetch('/employee/myrequests', {
            credentials: 'include'
        });
        
        if (response.ok) {
            const data = await response.json();
            updateExpensesList(data.expenses);
        }
    } catch (error) {
        console.error('Error loading requests:', error);
    }
}

function updateExpensesList(expenses) {
    const expensesList = document.getElementById('expensesList');
    
    if (expenses.length === 0) {
        expensesList.innerHTML = `
            <div class="text-center py-8 text-gray-500">
                <p>No expense requests yet</p>
            </div>
        `;
        return;
    }
    
    expensesList.innerHTML = expenses.map(expense => {
        const statusColor = {
            pending: 'bg-yellow-100 text-yellow-800',
            approved: 'bg-green-100 text-green-800',
            rejected: 'bg-red-100 text-red-800'
        };
        
        return `
            <div class="border border-gray-200 rounded-lg p-4">
                <div class="flex justify-between items-start mb-3">
                    <div>
                        <h3 class="font-semibold text-gray-800">To: ${expense.admin_name}</h3>
                        <p class="text-sm text-gray-600">${new Date(expense.created_at).toLocaleDateString()}</p>
                    </div>
                    <div class="text-right">
                        <p class="text-lg font-bold text-gray-900">$${expense.amount.toLocaleString()}</p>
                        <span class="inline-block px-2 py-1 text-xs font-semibold rounded-full ${statusColor[expense.status]}">
                            ${expense.status.charAt(0).toUpperCase() + expense.status.slice(1)}
                        </span>
                    </div>
                </div>
                
                <div class="mb-2">
                    <p class="text-sm text-gray-700">${expense.reason}</p>
                </div>
            </div>
        `;
    }).join('');
}

async function handleSubmitExpense(e) {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    const data = {
        admin_id: parseInt(formData.get('adminSelect')),
        amount: parseFloat(formData.get('amount')),
        reason: formData.get('reason')
    };
    
    try {
        const response = await fetch('/employee/submit', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data),
            credentials: 'include'
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showMessage('Expense submitted successfully!', 'success');
            e.target.reset();
            loadMyRequests();
        } else {
            showMessage(result.error || 'Failed to submit expense', 'error');
        }
    } catch (error) {
        showMessage('Error submitting expense', 'error');
    }
}

async function handleLogout() {
    try {
        await fetch('/auth/logout', {
            method: 'POST',
            credentials: 'include'
        });
        window.location.href = '/';
    } catch (error) {
        console.error('Error logging out:', error);
    }
}

function showMessage(message, type) {
    const messageDiv = document.getElementById('message');
    messageDiv.className = `fixed bottom-4 right-4 max-w-sm p-4 rounded-lg shadow-lg ${
        type === 'success' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
    }`;
    messageDiv.textContent = message;
    
    setTimeout(() => {
        messageDiv.textContent = '';
        messageDiv.className = 'fixed bottom-4 right-4 max-w-sm';
    }, 5000);
}