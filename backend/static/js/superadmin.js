// At the top of each dashboard JS file
document.addEventListener('DOMContentLoaded', async function() {
    const res = await fetch('/auth/check-session', { credentials: 'include' });
    if (res.status !== 200) {
        window.location.href = '/';
        return;
    }
    // ...rest of your dashboard code...
});let budgetChart;

document.addEventListener('DOMContentLoaded', function() {
    loadUserInfo();
    loadOverview();
    loadAdmins();
    loadTransactions();
    
    document.getElementById('allocateForm').addEventListener('submit', handleAllocate);
    // In all dashboard JS files
document.getElementById('logoutBtn').addEventListener('click', async function() {
    await fetch('/auth/logout', { method: 'POST', credentials: 'include' });
    localStorage.clear();
    window.location.href = '/';
});
    
    // Refresh data every 30 seconds
    setInterval(() => {
        loadOverview();
        loadTransactions();
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

async function loadAdmins() {
    try {
        const response = await fetch('/superadmin/admins', {
            credentials: 'include'
        });
        
        if (response.ok) {
            const data = await response.json();
            const adminSelect = document.getElementById('adminSelect');
            adminSelect.innerHTML = '<option value="">Choose an admin...</option>';
            
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

async function loadOverview() {
    try {
        const response = await fetch('/superadmin/overview', {
            credentials: 'include'
        });
        
        if (response.ok) {
            const data = await response.json();
            updateStatsCards(data.stats);
            updateBudgetChart(data.budgets);
            updateBudgetTable(data.budgets);
        }
    } catch (error) {
        console.error('Error loading overview:', error);
    }
}

async function loadTransactions() {
    try {
        const response = await fetch('/superadmin/transactions', {
            credentials: 'include'
        });
        
        if (response.ok) {
            const data = await response.json();
            updateTransactionsTable(data.transactions);
        }
    } catch (error) {
        console.error('Error loading transactions:', error);
    }
}

function updateStatsCards(stats) {
    document.getElementById('totalAllocated').textContent = `₹${stats.total_allocated.toFixed(2)}`;
    document.getElementById('totalSpent').textContent = `₹${stats.total_spent.toFixed(2)}`;
    document.getElementById('pendingRequests').textContent = stats.pending_expenses;
    document.getElementById('activeAdmins').textContent = stats.active_admins;
}

function updateBudgetChart(budgets) {
    const ctx = document.getElementById('budgetChart').getContext('2d');
    
    if (budgetChart) {
        budgetChart.destroy();
    }
    
    const labels = budgets.map(b => b.admin_name);
    const allocatedData = budgets.map(b => b.allocated);
    const spentData = budgets.map(b => b.spent);
    const remainingData = budgets.map(b => b.remaining);
    
    budgetChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Allocated',
                    data: allocatedData,
                    backgroundColor: 'rgba(59, 130, 246, 0.8)',
                    borderColor: 'rgba(59, 130, 246, 1)',
                    borderWidth: 1
                },
                {
                    label: 'Spent',
                    data: spentData,
                    backgroundColor: 'rgba(239, 68, 68, 0.8)',
                    borderColor: 'rgba(239, 68, 68, 1)',
                    borderWidth: 1
                },
                {
                    label: 'Remaining',
                    data: remainingData,
                    backgroundColor: 'rgba(34, 197, 94, 0.8)',
                    borderColor: 'rgba(34, 197, 94, 1)',
                    borderWidth: 1
                }
            ]
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
                            return context.dataset.label + ': ₹' + context.parsed.y.toLocaleString();
                        }
                    }
                }
            }
        }
    });
}

function updateBudgetTable(budgets) {
    const tbody = document.getElementById('budgetTableBody');
    tbody.innerHTML = '';
    
    if (budgets.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="5" class="px-6 py-4 text-center text-gray-500">
                    No budget allocations found
                </td>
            </tr>
        `;
        return;
    }
    
    budgets.forEach(budget => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td class="px-6 py-4 whitespace-nowrap">
                <div class="text-sm font-medium text-gray-900">${budget.admin_name}</div>
                <div class="text-sm text-gray-500">${budget.admin_email}</div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                ₹${budget.allocated.toFixed(2)}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                ₹${budget.spent.toFixed(2)}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                ₹${budget.remaining.toFixed(2)}
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
                <div class="flex items-center">
                    <div class="flex-1 bg-gray-200 rounded-full h-2 mr-2">
                        <div class="bg-blue-600 h-2 rounded-full" style="width: ${budget.usage_percentage}%"></div>
                    </div>
                    <span class="text-sm text-gray-900">${budget.usage_percentage}%</span>
                </div>
            </td>
        `;
        tbody.appendChild(row);
    });
}

function updateTransactionsTable(transactions) {
    const tbody = document.getElementById('transactionsTableBody');
    tbody.innerHTML = '';
    
    if (transactions.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="px-6 py-4 text-center text-gray-500">
                    No transactions found
                </td>
            </tr>
        `;
        return;
    }
    
    transactions.forEach(transaction => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                ${new Date(transaction.timestamp).toLocaleDateString()}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                ${transaction.sender_name}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                ${transaction.receiver_name}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                ₹${transaction.amount.toFixed(2)}
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
                <span class="inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                    transaction.type === 'allocation' ? 'bg-blue-100 text-blue-800' : 'bg-green-100 text-green-800'
                }">
                    ${transaction.type.charAt(0).toUpperCase() + transaction.type.slice(1)}
                </span>
            </td>
            <td class="px-6 py-4 text-sm text-gray-900 max-w-xs truncate">
                ${transaction.reason}
            </td>
        `;
        tbody.appendChild(row);
    });
}

async function handleAllocate(e) {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    const data = {
        admin_id: parseInt(formData.get('adminSelect')),
        amount: parseFloat(formData.get('amount'))
    };
    
    try {
        const response = await fetch('/superadmin/allocate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data),
            credentials: 'include'
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showMessage('Budget allocated successfully!', 'success');
            e.target.reset();
            loadOverview();
            loadTransactions();
        } else {
            showMessage(result.error || 'Failed to allocate budget', 'error');
        }
    } catch (error) {
        showMessage('Error allocating budget', 'error');
    }
}

document.getElementById('addClientForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    const name = document.getElementById('clientName').value.trim();
    const email = document.getElementById('clientEmail').value.trim();
    if (!name || !email) return showMessage('All fields required', 'error');
    const data = { name, email, password: 'password' };
    try {
        const res = await fetch('/superadmin/add-client', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
            credentials: 'include'
        });
        const result = await res.json();
        if (res.ok) {
            showMessage('Client added! Default password: password', 'success');
            this.reset();
            loadAdmins();
        } else {
            showMessage(result.error || 'Failed to add client', 'error');
        }
    } catch {
        showMessage('Error adding client', 'error');
    }
});

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

let systemAnalyticsChart, adminComparisonChart, activityTrendChart;

async function loadSystemAnalytics() {
    try {
        const response = await fetch('/ai/superadmin/system-analytics', { credentials: 'include' });
        if (response.ok) {
            const data = await response.json();
            updateSystemAnalyticsDisplay(data);
            updateAdminComparisonChart(data.admin_performance);
            updateActivityTrendChart(data.activity_trends);
            displaySystemInsights(data.insights);
        }
    } catch (error) {
        console.error('Error loading system analytics:', error);
    }
}

function updateSystemAnalyticsDisplay(data) {
    // Update KPI cards
    document.getElementById('systemTotalTransactions').textContent = data.system_metrics.total_transactions;
    document.getElementById('systemTotalAdmins').textContent = data.system_metrics.total_admins;
    document.getElementById('systemAvgUtilization').textContent = `${data.system_metrics.avg_utilization}%`;

    // Update approval rates chart
    updateApprovalRatesChart(data.approval_rates);
}

function updateApprovalRatesChart(approvalData) {
    const ctx = document.getElementById('approvalRatesChart');
    if (!ctx) return;

    new Chart(ctx, {
        type: 'pie',
        data: {
            labels: Object.keys(approvalData).map(status => status.charAt(0).toUpperCase() + status.slice(1)),
            datasets: [{
                data: Object.values(approvalData).map(data => data.percentage),
                backgroundColor: ['#10B981', '#F59E0B', '#EF4444'],
                hoverOffset: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'System-wide Approval Rates'
                },
                legend: {
                    position: 'bottom'
                }
            }
        }
    });
}

function updateAdminComparisonChart(adminData) {
    const ctx = document.getElementById('adminComparisonChart');
    if (!ctx) return;

    if (adminComparisonChart) {
        adminComparisonChart.destroy();
    }

    adminComparisonChart = new Chart(ctx, {
        type: 'scatter',
        data: {
            datasets: [{
                label: 'Admin Performance',
                data: adminData.map(admin => ({
                    x: admin.utilization_rate,
                    y: admin.efficiency_score,
                    label: admin.admin_name
                })),
                backgroundColor: 'rgba(59, 130, 246, 0.6)',
                borderColor: 'rgb(59, 130, 246)',
                pointRadius: 8,
                pointHoverRadius: 12
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'Admin Performance Matrix'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const point = context.raw;
                            return `${point.label}: Utilization ${point.x}%, Efficiency ${point.y}`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: 'Budget Utilization (%)'
                    },
                    min: 0,
                    max: 100
                },
                y: {
                    title: {
                        display: true,
                        text: 'Efficiency Score'
                    },
                    min: 0,
                    max: 100
                }
            }
        }
    });
}

function updateActivityTrendChart(activityData) {
    const ctx = document.getElementById('activityTrendChart');
    if (!ctx) return;

    if (activityTrendChart) {
        activityTrendChart.destroy();
    }

    activityTrendChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: activityData.map(d => new Date(d.date).toLocaleDateString()),
            datasets: [
                {
                    label: 'Daily Amount (₹)',
                    data: activityData.map(d => d.total_amount),
                    borderColor: 'rgb(34, 197, 94)',
                    backgroundColor: 'rgba(34, 197, 94, 0.1)',
                    tension: 0.4,
                    fill: true
                },
                {
                    label: 'Transaction Count',
                    data: activityData.map(d => d.transaction_count),
                    borderColor: 'rgb(239, 68, 68)',
                    backgroundColor: 'rgba(239, 68, 68, 0.1)',
                    yAxisID: 'y1',
                    tension: 0.4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'System Activity Trends (Last 90 Days)'
                }
            },
            scales: {
                y: {
                    title: {
                        display: true,
                        text: 'Amount (₹)'
                    }
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    title: {
                        display: true,
                        text: 'Transaction Count'
                    },
                    grid: {
                        drawOnChartArea: false,
                    }
                }
            }
        }
    });
}

function displaySystemInsights(insights) {
    const container = document.getElementById('systemInsightsContainer');
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
                    <p class="text-xs mt-2 opacity-75"><strong>Recommendation:</strong> ${insight.recommendation}</p>
                </div>
            </div>
        `;
        
        container.appendChild(insightCard);
    });
}

// Add to your existing DOMContentLoaded event
document.addEventListener('DOMContentLoaded', function() {
    // ... existing code ...
    loadSystemAnalytics();
    
    // Refresh system analytics every 10 minutes
    setInterval(loadSystemAnalytics, 600000);
});