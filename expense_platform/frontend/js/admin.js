let budgetChart, employeeChart;

document.addEventListener('DOMContentLoaded', function() {
    loadUserInfo();
    loadDashboard();
    loadPendingExpenses();
    loadEmployeeStats();
    
    document.getElementById('logoutBtn').addEventListener('click', handleLogout);
    
    // Refresh data every 30 seconds
    setInterval(() => {
        loadDashboard();
        loadPendingExpenses();
        loadEmployeeStats();
    }, 30000);
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

async function loadDashboard() {
    try {
        const response = await fetch('/admin/dashboard', {
            credentials: 'include'
        });
        
        if (response.ok) {
            const data = await response.json();
            updateDashboardCards(data);
            updateBudgetChart(data.budget);
        }
    } catch (error) {
        console.error('Error loading dashboard:', error);
    }
}

function updateDashboardCards(data) {
    document.getElementById('totalBudget').textContent = `₹${data.budget.total_budget.toFixed(2)}`;
    document.getElementById('totalSpent').textContent = `₹${data.budget.total_spent.toFixed(2)}`;
    document.getElementById('remaining').textContent = `₹${data.budget.remaining.toFixed(2)}`;
    document.getElementById('pendingCount').textContent = data.pending_count;
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
                data: [budget.total_spent, budget.remaining],
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
                            return context.label + ': ₹' + context.parsed.toLocaleString();
                        }
                    }
                }
            }
        }
    });
}

async function loadPendingExpenses() {
    try {
        const response = await fetch('/admin/expenses', {
            credentials: 'include'
        });
        
        if (response.ok) {
            const data = await response.json();
            updatePendingExpenses(data.expenses);
        }
    } catch (error) {
        console.error('Error loading expenses:', error);
    }
}

function updatePendingExpenses(expenses) {
    const tbody = document.getElementById('pendingExpensesBody');
    tbody.innerHTML = '';
    
    if (expenses.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="5" class="px-6 py-4 text-center text-gray-500">
                    No pending expense requests
                </td>
            </tr>
        `;
        return;
    }
    
    expenses.forEach(expense => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td class="px-6 py-4 whitespace-nowrap">
                <div class="text-sm font-medium text-gray-900">${expense.employee_name}</div>
                <div class="text-sm text-gray-500">${expense.employee_email}</div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                ₹${expense.amount.toFixed(2)}
            </td>
            <td class="px-6 py-4 text-sm text-gray-900 max-w-xs truncate">
                ${expense.reason}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                ${new Date(expense.created_at).toLocaleDateString()}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm space-x-2">
                <button onclick="approveExpense(${expense.id})" 
                    class="bg-green-600 text-white px-3 py-1 rounded text-xs hover:bg-green-700">
                    Approve
                </button>
                <button onclick="rejectExpense(${expense.id})" 
                    class="bg-red-600 text-white px-3 py-1 rounded text-xs hover:bg-red-700">
                    Reject
                </button>
            </td>
        `;
        tbody.appendChild(row);
    });
}

async function loadEmployeeStats() {
    try {
        const response = await fetch('/admin/employee-stats', {
            credentials: 'include'
        });
        
        if (response.ok) {
            const data = await response.json();
            updateEmployeeStats(data.employees);
            updateEmployeeChart(data.employees);
        }
    } catch (error) {
        console.error('Error loading employee stats:', error);
    }
}

function updateEmployeeStats(employees) {
    const tbody = document.getElementById('employeeStatsBody');
    tbody.innerHTML = '';
    
    if (employees.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="px-6 py-4 text-center text-gray-500">
                    No employee data found
                </td>
            </tr>
        `;
        return;
    }
    
    employees.forEach(employee => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td class="px-6 py-4 whitespace-nowrap">
                <div class="text-sm font-medium text-gray-900">${employee.name}</div>
                <div class="text-sm text-gray-500">${employee.email}</div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${employee.total_requests}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">₹${employee.total_amount.toFixed(2)}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-green-600">${employee.approved}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-yellow-600">${employee.pending}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-red-600">${employee.rejected}</td>
        `;
        tbody.appendChild(row);
    });
}

function updateEmployeeChart(employees) {
    const ctx = document.getElementById('employeeChart').getContext('2d');
    
    if (employeeChart) {
        employeeChart.destroy();
    }
    
    const labels = employees.map(e => e.name);
    const spendingData = employees.map(e => e.approved_amount);
    
    employeeChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Approved Amount',
                data: spendingData,
                backgroundColor: 'rgba(34, 197, 94, 0.8)',
                borderColor: 'rgba(34, 197, 94, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return '₹' + value.toLocaleString();
                        }
                    }
                }
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return 'Approved: ₹' + context.parsed.y.toLocaleString();
                        }
                    }
                }
            }
        }
    });
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
            loadDashboard();
            loadPendingExpenses();
            loadEmployeeStats();
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
            loadEmployeeStats();
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