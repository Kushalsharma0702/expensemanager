let budgetChart;

document.addEventListener('DOMContentLoaded', function() {
    loadUserInfo();
    loadBudget();
    loadPendingExpenses();
    
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

async function loadBudget() {
    try {
        const response = await fetch('/admin/budget', {
            credentials: 'include'
        });
        
        if (response.ok) {
            const budget = await response.json();
            updateBudgetChart(budget);
            updateBudgetInfo(budget);
        }
    } catch (error) {
        console.error('Error loading budget:', error);
    }
}

function updateBudgetChart(budget) {
    const ctx = document.getElementById('budgetChart').getContext('2d');
    
    if (budgetChart) {
        budgetChart.destroy();
    }
    
    budgetChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Spent', 'Remaining'],
            datasets: [{
                data: [budget.spent, budget.remaining],
                backgroundColor: ['#EF4444', '#22C55E'],
                borderColor: ['#DC2626', '#16A34A'],
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return context.label + ': $' + context.parsed.toLocaleString();
                        }
                    }
                }
            }
        }
    });
}

function updateBudgetInfo(budget) {
    const budgetInfo = document.getElementById('budgetInfo');
    const usagePercent = budget.allocated > 0 ? (budget.spent / budget.allocated * 100).toFixed(1) : 0;
    
    budgetInfo.innerHTML = `
        <div class="flex justify-between">
            <span class="text-sm text-gray-600">Allocated:</span>
            <span class="text-sm font-medium">$${budget.allocated.toLocaleString()}</span>
        </div>
        <div class="flex justify-between">
            <span class="text-sm text-gray-600">Spent:</span>
            <span class="text-sm font-medium text-red-600">$${budget.spent.toLocaleString()}</span>
        </div>
        <div class="flex justify-between">
            <span class="text-sm text-gray-600">Remaining:</span>
            <span class="text-sm font-medium text-green-600">$${budget.remaining.toLocaleString()}</span>
        </div>
        <div class="flex justify-between">
            <span class="text-sm text-gray-600">Usage:</span>
            <span class="text-sm font-medium">${usagePercent}%</span>
        </div>
    `;
}

async function loadPendingExpenses() {
    try {
        const response = await fetch('/admin/expenses', {
            credentials: 'include'
        });
        
        if (response.ok) {
            const data = await response.json();
            updateExpensesList(data.expenses);
        }
    } catch (error) {
        console.error('Error loading expenses:', error);
    }
}

function updateExpensesList(expenses) {
    const expensesList = document.getElementById('expensesList');
    
    if (expenses.length === 0) {
        expensesList.innerHTML = `
            <div class="text-center py-8 text-gray-500">
                <p>No pending expense requests</p>
            </div>
        `;
        return;
    }
    
    expensesList.innerHTML = expenses.map(expense => `
        <div class="border border-gray-200 rounded-lg p-4">
            <div class="flex justify-between items-start mb-3">
                <div>
                    <h3 class="font-semibold text-gray-800">${expense.employee_name}</h3>
                    <p class="text-sm text-gray-600">${expense.employee_email}</p>
                </div>
                <div class="text-right">
                    <p class="text-lg font-bold text-gray-900">$${expense.amount.toLocaleString()}</p>
                    <p class="text-xs text-gray-500">${new Date(expense.created_at).toLocaleDateString()}</p>
                </div>
            </div>
            
            <div class="mb-4">
                <p class="text-sm text-gray-700">${expense.reason}</p>
            </div>
            
            <div class="flex gap-2">
                <button 
                    onclick="approveExpense(${expense.id})"
                    class="flex-1 bg-green-600 text-white py-2 px-4 rounded-lg hover:bg-green-700 transition-colors"
                >
                    Approve
                </button>
                <button 
                    onclick="rejectExpense(${expense.id})"
                    class="flex-1 bg-red-600 text-white py-2 px-4 rounded-lg hover:bg-red-700 transition-colors"
                >
                    Reject
                </button>
            </div>
        </div>
    `).join('');
}

async function approveExpense(expenseId) {
    try {
        const response = await fetch('/admin/approve', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ expense_id: expenseId }),
            credentials: 'include'
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showMessage('Expense approved successfully!', 'success');
            loadPendingExpenses();
            loadBudget();
        } else {
            showMessage(result.error || 'Failed to approve expense', 'error');
        }
    } catch (error) {
        showMessage('Error approving expense', 'error');
    }
}

async function rejectExpense(expenseId) {
    try {
        const response = await fetch('/admin/reject', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ expense_id: expenseId }),
            credentials: 'include'
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showMessage('Expense rejected successfully!', 'success');
            loadPendingExpenses();
        } else {
            showMessage(result.error || 'Failed to reject expense', 'error');
        }
    } catch (error) {
        showMessage('Error rejecting expense', 'error');
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