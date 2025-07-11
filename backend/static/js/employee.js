// At the top of each dashboard JS file
document.addEventListener('DOMContentLoaded', async function() {
    const res = await fetch('/auth/check-session', { credentials: 'include' });
    if (res.status !== 200) {
        window.location.href = '/';
        return;
    }
    // ...rest of your dashboard code...
});
document.addEventListener('DOMContentLoaded', function() {
    loadUserInfo();
    loadAdmins();
    loadStats();
    loadMyRequests();
    loadEmployeeInsights();
    
    // Logout functionality
    // In all dashboard JS files
// In all dashboard JS files
document.getElementById('logoutBtn').addEventListener('click', async function() {
    await fetch('/auth/logout', { method: 'POST', credentials: 'include' });
    localStorage.clear();
    window.location.href = '/';
});
    // Expense form submission
    document.getElementById('expenseForm').addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const formData = new FormData(this);
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
                this.reset();
                loadStats();
                loadMyRequests();
            } else {
                showMessage(result.error || 'Failed to submit expense', 'error');
            }
        } catch (error) {
            console.error('Error submitting expense:', error);
            showMessage('Error submitting expense', 'error');
        }
    });
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
            
            // Clear existing options except the first one
            adminSelect.innerHTML = '<option value="">Choose an admin...</option>';
            
            data.admins.forEach(admin => {
                const option = document.createElement('option');
                option.value = admin.id;
                option.textContent = `${admin.name} (Budget: ₹${admin.available_budget.toFixed(2)})`;
                adminSelect.appendChild(option);
            });
        } else {
            console.error('Failed to load admins');
            showMessage('Failed to load admin list', 'error');
        }
    } catch (error) {
        console.error('Error loading admins:', error);
        showMessage('Error loading admin list', 'error');
    }
}

let statusChart;

async function loadStats() {
    try {
        const response = await fetch('/employee/stats', {
            credentials: 'include'
        });
        
        if (response.ok) {
            const stats = await response.json();
            updateStatsCards(stats);
            updateStatusChart(stats);
        } else {
            console.error('Failed to load stats');
        }
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

function updateStatsCards(stats) {
    document.getElementById('totalRequests').textContent = stats.total_requests;
    document.getElementById('approvedRequests').textContent = stats.approved_requests;
    document.getElementById('pendingRequests').textContent = stats.pending_requests;
    document.getElementById('rejectedRequests').textContent = stats.rejected_requests;
}

function updateStatusChart(stats) {
    const ctx = document.getElementById('statusChart').getContext('2d');
    
    if (statusChart) {
        statusChart.destroy();
    }
    
    statusChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Approved', 'Pending', 'Rejected'],
            datasets: [{
                data: [stats.approved_requests, stats.pending_requests, stats.rejected_requests],
                backgroundColor: [
                    '#10B981', // Green
                    '#F59E0B', // Yellow
                    '#EF4444'  // Red
                ],
                borderWidth: 2,
                borderColor: '#fff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    });
}

async function loadMyRequests() {
    try {
        const response = await fetch('/employee/myrequests', {
            credentials: 'include'
        });
        
        if (response.ok) {
            const data = await response.json();
            updateExpensesList(data.expenses);
        } else {
            console.error('Failed to load requests');
        }
    } catch (error) {
        console.error('Error loading requests:', error);
    }
}

function updateExpensesList(expenses) {
    const tbody = document.getElementById('expensesTableBody');
    tbody.innerHTML = '';
    
    if (expenses.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="5" class="px-6 py-4 text-center text-gray-500">
                    No expense requests found
                </td>
            </tr>
        `;
        return;
    }
    
    expenses.forEach(expense => {
        const row = document.createElement('tr');
        
        const statusBadgeClass = {
            'pending': 'bg-yellow-100 text-yellow-800',
            'approved': 'bg-green-100 text-green-800',
            'rejected': 'bg-red-100 text-red-800'
        }[expense.status] || 'bg-gray-100 text-gray-800';
        
        row.innerHTML = `
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                ${new Date(expense.created_at).toLocaleDateString()}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                ${expense.admin_name}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                ₹${expense.amount.toFixed(2)}
            </td>
            <td class="px-6 py-4 text-sm text-gray-900 max-w-xs truncate">
                ${expense.reason}
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
                <span class="inline-flex px-2 py-1 text-xs font-semibold rounded-full ${statusBadgeClass}">
                    ${expense.status.charAt(0).toUpperCase() + expense.status.slice(1)}
                </span>
            </td>
        `;
        
        tbody.appendChild(row);
    });
}

function showMessage(message, type) {
    const messageDiv = document.getElementById('message');
    messageDiv.className = `fixed bottom-4 right-4 max-w-sm p-4 rounded-lg shadow-lg ${
        type === 'success' ? 'bg-green-500 text-white' : 'bg-red-500 text-white'
    }`;
    messageDiv.textContent = message;
    
    setTimeout(() => {
        messageDiv.textContent = '';
        messageDiv.className = 'fixed bottom-4 right-4 max-w-sm';
    }, 5000);
}

let employeeSpendingChart, employeeStatusChart;

async function loadEmployeeInsights() {
    try {
        const response = await fetch('/ai/employee/spending-insights', { credentials: 'include' });
        if (response.ok) {
            const data = await response.json();
            updateEmployeeSpendingChart(data.monthly_trends);
            updateEmployeeStatusChart(data.status_breakdown);
            displayEmployeeInsights(data.insights);
            updateResponseTimeDisplay(data.avg_response_time_hours);
        }
    } catch (error) {
        console.error('Error loading employee insights:', error);
    }
}

function updateEmployeeSpendingChart(monthlyData) {
    const ctx = document.getElementById('employeeSpendingChart');
    if (!ctx) return;

    if (employeeSpendingChart) {
        employeeSpendingChart.destroy();
    }

    employeeSpendingChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: monthlyData.map(d => d.period),
            datasets: [{
                label: 'Monthly Spending (₹)',
                data: monthlyData.map(d => d.total_amount),
                backgroundColor: 'rgba(59, 130, 246, 0.8)',
                borderColor: 'rgb(59, 130, 246)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'Your Monthly Spending Trend'
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Amount (₹)'
                    }
                }
            }
        }
    });
}

function updateEmployeeStatusChart(statusData) {
    const ctx = document.getElementById('employeeStatusChart');
    if (!ctx) return;

    if (employeeStatusChart) {
        employeeStatusChart.destroy();
    }

    const labels = Object.keys(statusData);
    const data = Object.values(statusData).map(item => item.count);
    const backgroundColors = {
        'approved': '#10B981',
        'pending': '#F59E0B',
        'rejected': '#EF4444'
    };

    employeeStatusChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels.map(label => label.charAt(0).toUpperCase() + label.slice(1)),
            datasets: [{
                data: data,
                backgroundColor: labels.map(label => backgroundColors[label] || '#6B7280'),
                hoverOffset: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'Your Request Status Breakdown'
                },
                legend: {
                    position: 'bottom'
                }
            }
        }
    });
}

function updateResponseTimeDisplay(avgResponseHours) {
    const element = document.getElementById('avgResponseTime');
    if (element) {
        if (avgResponseHours < 24) {
            element.textContent = `${avgResponseHours.toFixed(1)} hours`;
            element.className = 'text-green-600 font-semibold';
        } else if (avgResponseHours < 72) {
            element.textContent = `${avgResponseHours.toFixed(1)} hours`;
            element.className = 'text-yellow-600 font-semibold';
        } else {
            element.textContent = `${avgResponseHours.toFixed(1)} hours`;
            element.className = 'text-red-600 font-semibold';
        }
    }
}

function displayEmployeeInsights(insights) {
    const container = document.getElementById('employeeInsightsContainer');
    if (!container) return;

    container.innerHTML = '';

    insights.forEach(insight => {
        const insightCard = document.createElement('div');
        insightCard.className = `p-4 rounded-lg border-l-4 mb-4 ${getInsightClasses(insight.type)}`;
        
        insightCard.innerHTML = `
            <div class="flex items-start">
                <div class="flex-shrink-0">
                    ${getInsightIcon(insight.type)}
                </div>
                <div class="ml-3">
                    <h4 class="text-sm font-medium">${insight.title}</h4>
                    <p class="text-sm mt-1">${insight.message}</p>
                    <p class="text-xs mt-2 opacity-75"><strong>Tip:</strong> ${insight.recommendation}</p>
                </div>
            </div>
        `;
        
        container.appendChild(insightCard);
    });
}

// Add to your existing DOMContentLoaded event
document.addEventListener('DOMContentLoaded', function() {
    // ... existing code ...
    loadEmployeeInsights();
    
    // Refresh employee insights every 15 minutes
    setInterval(loadEmployeeInsights, 900000);
});