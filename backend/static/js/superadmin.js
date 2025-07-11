// Session check - runs first
document.addEventListener('DOMContentLoaded', async function() {
    const res = await fetch('/auth/check-session', { credentials: 'include' });
    if (res.status !== 200) {
        window.location.href = '/';
        return;
    }
});

let budgetChart;

// Main DOMContentLoaded event - runs once
document.addEventListener('DOMContentLoaded', function() {
    loadUserInfo();
    loadOverview();
    loadAdmins();
    loadTransactions();
    
    // Allocate form handler
    const allocateForm = document.getElementById('allocateForm');
    if (allocateForm) {
        allocateForm.addEventListener('submit', handleAllocate);
    }
    
    // Logout functionality
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', async function() {
            try {
                await fetch('/auth/logout', { method: 'POST', credentials: 'include' });
                localStorage.clear();
                sessionStorage.clear();
                window.location.href = '/';
            } catch (error) {
                console.error('Logout error:', error);
                window.location.href = '/';
            }
        });
    }
    
    // Add Client form handler
    const addClientForm = document.getElementById('addClientForm');
    if (addClientForm) {
        addClientForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            const name = document.getElementById('clientName').value.trim();
            const email = document.getElementById('clientEmail').value.trim();
            const phone = document.getElementById('clientPhone').value.trim();
            const password = document.getElementById('clientPassword').value.trim();
            
            if (!name || !email || !phone || !password) {
                showMessage('All fields are required', 'error');
                return;
            }
            
            try {
                const response = await fetch('/superadmin/add-client', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name, email, phone, password }),
                    credentials: 'include'
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    showMessage('Client added successfully!', 'success');
                    this.reset();
                    loadAdmins();
                    loadOverview();
                } else {
                    showMessage(result.error || 'Failed to add client', 'error');
                }
            } catch (error) {
                console.error('Error adding client:', error);
                showMessage('Error adding client', 'error');
            }
        });
    }
    
    // Add Employee form handler
    const addEmployeeForm = document.getElementById('addEmployeeForm');
    if (addEmployeeForm) {
        addEmployeeForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            const name = document.getElementById('employeeName').value.trim();
            const email = document.getElementById('employeeEmail').value.trim();
            const phone = document.getElementById('employeePhone').value.trim();
            const password = document.getElementById('employeePassword').value.trim();
            const adminId = document.getElementById('employeeAdmin').value;
            
            if (!name || !email || !phone || !password || !adminId) {
                showMessage('All fields are required', 'error');
                return;
            }
            
            try {
                const response = await fetch('/superadmin/add-employee', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        name, 
                        email, 
                        phone, 
                        password, 
                        created_by: parseInt(adminId) 
                    }),
                    credentials: 'include'
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    showMessage('Employee added successfully!', 'success');
                    this.reset();
                } else {
                    showMessage(result.error || 'Failed to add employee', 'error');
                }
            } catch (error) {
                console.error('Error adding employee:', error);
                showMessage('Error adding employee', 'error');
            }
        });
    }
    
    // Populate admin selects
    populateAdminSelect();
    
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
            updateAdminCards(data.budgets);
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
    document.getElementById('adminAllocated').textContent = `₹${stats.admin_allocated || 0}`;
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

function updateAdminCards(budgets) {
    const container = document.getElementById('adminCardsContainer');
    container.innerHTML = '';
    
    if (budgets.length === 0) {
        container.innerHTML = `
            <div class="col-span-full text-center py-8">
                <div class="text-gray-500">
                    <svg class="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"></path>
                    </svg>
                    <h3 class="mt-2 text-sm font-medium text-gray-900">No admins found</h3>
                    <p class="mt-1 text-sm text-gray-500">Get started by adding a new admin.</p>
                </div>
            </div>
        `;
        return;
    }
    
    budgets.forEach(budget => {
        const card = document.createElement('div');
        card.className = 'bg-white rounded-xl shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow';
        
        const usageColor = budget.usage_percentage > 80 ? 'bg-red-500' : 
                          budget.usage_percentage > 60 ? 'bg-yellow-500' : 'bg-green-500';
        
        card.innerHTML = `
            <div class="flex items-start justify-between">
                <div class="flex items-center">
                    <div class="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                        <svg class="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"></path>
                        </svg>
                    </div>
                    <div class="ml-3">
                        <h3 class="text-lg font-semibold text-gray-900">${budget.admin_name}</h3>
                        <p class="text-sm text-gray-600">${budget.admin_email}</p>
                        <p class="text-sm text-gray-500">${budget.admin_phone || 'No phone'}</p>
                    </div>
                </div>
                <div class="flex space-x-2">
                    <button onclick="editAdmin(${budget.admin_id}, '${budget.admin_name}', '${budget.admin_email}', '${budget.admin_phone || ''}')" 
                            class="p-2 text-blue-600 hover:bg-blue-50 rounded-lg" title="Edit Admin">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"></path>
                        </svg>
                    </button>
                    <button onclick="openAllocateModal('${budget.admin_name}', ${budget.admin_id})" 
                            class="p-2 text-green-600 hover:bg-green-50 rounded-lg" title="Allocate Budget">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1"></path>
                        </svg>
                    </button>
                </div>
            </div>
            
            <div class="mt-4">
                <div class="grid grid-cols-3 gap-4">
                    <div class="text-center">
                        <div class="text-2xl font-bold text-blue-600">₹${budget.allocated.toFixed(0)}</div>
                        <div class="text-xs text-gray-500">Allocated</div>
                    </div>
                    <div class="text-center">
                        <div class="text-2xl font-bold text-red-600">₹${budget.spent.toFixed(0)}</div>
                        <div class="text-xs text-gray-500">Spent</div>
                    </div>
                    <div class="text-center">
                        <div class="text-2xl font-bold text-green-600">₹${budget.remaining.toFixed(0)}</div>
                        <div class="text-xs text-gray-500">Remaining</div>
                    </div>
                </div>
                
                <div class="mt-4">
                    <div class="flex items-center justify-between text-sm text-gray-600 mb-1">
                        <span>Budget Usage</span>
                        <span>${budget.usage_percentage}%</span>
                    </div>
                    <div class="w-full bg-gray-200 rounded-full h-2">
                        <div class="${usageColor} h-2 rounded-full transition-all duration-300" style="width: ${budget.usage_percentage}%"></div>
                    </div>
                </div>
            </div>
        `;
        
        container.appendChild(card);
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
    const phone = document.getElementById('clientPhone').value.trim();
    const password = document.getElementById('clientPassword').value.trim();
    if (!name || !email || !phone || !password) return showMessage('All fields required', 'error');
    const data = { name, email, phone, password };
    try {
        const res = await fetch('/superadmin/add-client', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
            credentials: 'include'
        });
        const result = await res.json();
        if (res.ok) {
            showMessage(`Client added! Password: ${password}`, 'success');
            this.reset();
            loadAdmins();
            loadOverview();
        } else {
            showMessage(result.error || 'Failed to add client', 'error');
        }
    } catch {
        showMessage('Error adding client', 'error');
    }
});

document.getElementById('addEmployeeForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    const name = document.getElementById('employeeName').value.trim();
    const email = document.getElementById('employeeEmail').value.trim();
    const phone = document.getElementById('employeePhone').value.trim();
    const adminId = document.getElementById('employeeAdmin').value;
    const statusDiv = document.getElementById('employeeFormStatus');
    if (!name || !email || !phone || !adminId) {
        statusDiv.textContent = 'All fields are required';
        statusDiv.className = 'mt-4 p-3 rounded-lg text-sm font-medium bg-red-100 text-red-800';
        statusDiv.classList.remove('hidden');
        return;
    }
    const data = { name, email, phone, password: 'password', created_by: parseInt(adminId) };
    try {
        const res = await fetch('/superadmin/add-employee', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
            credentials: 'include'
        });
        const result = await res.json();
        if (res.ok) {
            statusDiv.textContent = 'Employee added successfully! Default password: password';
            statusDiv.className = 'mt-4 p-3 rounded-lg text-sm font-medium bg-green-100 text-green-800';
            statusDiv.classList.remove('hidden');
            this.reset();
        } else {
            statusDiv.textContent = result.error || 'Failed to add employee';
            statusDiv.className = 'mt-4 p-3 rounded-lg text-sm font-medium bg-red-100 text-red-800';
            statusDiv.classList.remove('hidden');
        }
    } catch {
        statusDiv.textContent = 'Error adding employee';
        statusDiv.className = 'mt-4 p-3 rounded-lg text-sm font-medium bg-red-100 text-red-800';
        statusDiv.classList.remove('hidden');
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
    if (messageDiv) {
        messageDiv.className = `fixed bottom-4 right-4 max-w-sm p-4 rounded-lg shadow-lg ${
            type === 'success' ? 'bg-green-500 text-white' : 'bg-red-500 text-white'
        }`;
        messageDiv.textContent = message;
        messageDiv.style.display = 'block';
        
        setTimeout(() => {
            messageDiv.style.display = 'none';
        }, 5000);
    }
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

async function populateAdminSelect() {
    const select = document.getElementById('employeeAdmin');
    if (!select) return;
    select.innerHTML = '<option value="">Choose an admin...</option>';
    try {
        const res = await fetch('/superadmin/admins', { credentials: 'include' });
        if (res.ok) {
            const data = await res.json();
            data.admins.forEach(admin => {
                const option = document.createElement('option');
                option.value = admin.id;
                option.textContent = `${admin.name} (${admin.email})`;
                select.appendChild(option);
            });
        }
    } catch (e) {
        // handle error
    }
}
document.addEventListener('DOMContentLoaded', populateAdminSelect);

// EDIT ADMIN FUNCTION
function editAdmin(adminId, currentName, currentEmail, currentPhone) {
    // Remove any existing modal first
    const existingModal = document.getElementById('editAdminModal');
    if (existingModal) {
        existingModal.remove();
    }
    
    // Create modal HTML
    const modalHTML = `
        <div id="editAdminModal" class="fixed inset-0 z-50 overflow-y-auto" style="background-color: rgba(0, 0, 0, 0.5);">
            <div class="flex items-center justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
                <div class="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
                    <div class="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
                        <div class="sm:flex sm:items-start">
                            <div class="mt-3 text-center sm:mt-0 sm:ml-4 sm:text-left w-full">
                                <h3 class="text-lg leading-6 font-medium text-gray-900" id="modal-title">
                                    Edit Admin
                                </h3>
                                <div class="mt-2">
                                    <form id="editAdminForm">
                                        <div class="mb-4">
                                            <label class="block text-sm font-medium text-gray-700">Full Name</label>
                                            <input type="text" id="editAdminName" value="${currentName || ''}" 
                                                   class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500">
                                        </div>
                                        <div class="mb-4">
                                            <label class="block text-sm font-medium text-gray-700">Email</label>
                                            <input type="email" id="editAdminEmail" value="${currentEmail || ''}" 
                                                   class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500">
                                        </div>
                                        <div class="mb-4">
                                            <label class="block text-sm font-medium text-gray-700">Phone</label>
                                            <input type="tel" id="editAdminPhone" value="${currentPhone || ''}" 
                                                   class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500">
                                        </div>
                                        <div class="mb-4">
                                            <label class="block text-sm font-medium text-gray-700">New Password (leave blank to keep current)</label>
                                            <input type="password" id="editAdminPassword" placeholder="Enter new password (optional)" 
                                                   class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500">
                                        </div>
                                    </form>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
                        <button type="button" onclick="updateAdmin(${adminId})" 
                                class="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-indigo-600 text-base font-medium text-white hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:ml-3 sm:w-auto sm:text-sm">
                            Update Admin
                        </button>
                        <button type="button" onclick="closeEditAdminModal()" 
                                class="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm">
                            Cancel
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Add modal to body
    document.body.insertAdjacentHTML('beforeend', modalHTML);
    
    // Add click outside to close
    const modal = document.getElementById('editAdminModal');
    modal.addEventListener('click', function(e) {
        if (e.target === modal) {
            closeEditAdminModal();
        }
    });
}

// CLOSE MODALS
function closeEditAdminModal() {
    const modal = document.getElementById('editAdminModal');
    if (modal) {
        modal.style.opacity = '0';
        modal.style.transition = 'opacity 0.2s';
        setTimeout(() => {
            modal.remove();
        }, 200);
    }
}

// UPDATE ADMIN FUNCTION
async function updateAdmin(adminId) {
    const name = document.getElementById('editAdminName').value.trim();
    const email = document.getElementById('editAdminEmail').value.trim();
    const phone = document.getElementById('editAdminPhone').value.trim();
    const password = document.getElementById('editAdminPassword').value.trim();
    
    if (!name || !email || !phone) {
        showMessage('Name, email, and phone are required', 'error');
        return;
    }
    
    try {
        const requestBody = {
            admin_id: adminId,
            name: name,
            email: email,
            phone: phone
        };
        
        if (password) {
            requestBody.password = password;
        }
        
        const response = await fetch('/superadmin/edit-admin', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestBody),
            credentials: 'include'
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showMessage('Admin updated successfully!', 'success');
            closeEditAdminModal();
            loadOverview();
            loadAdmins();
        } else {
            showMessage(result.error || 'Failed to update admin', 'error');
        }
    } catch (error) {
        console.error('Error updating admin:', error);
        showMessage('Error updating admin', 'error');
    }
}

// EDIT EMPLOYEE FUNCTION (for superadmin)
function editEmployee(employeeId, currentName, currentEmail, currentPhone) {
    // Create modal HTML
    const modalHTML = `
        <div id="editEmployeeModal" class="fixed inset-0 z-50 overflow-y-auto" style="background-color: rgba(0, 0, 0, 0.5);">
            <div class="flex items-center justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
                <div class="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
                    <div class="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
                        <div class="sm:flex sm:items-start">
                            <div class="mt-3 text-center sm:mt-0 sm:ml-4 sm:text-left w-full">
                                <h3 class="text-lg leading-6 font-medium text-gray-900" id="modal-title">
                                    Edit Employee
                                </h3>
                                <div class="mt-2">
                                    <form id="editEmployeeForm">
                                        <div class="mb-4">
                                            <label class="block text-sm font-medium text-gray-700">Full Name</label>
                                            <input type="text" id="editEmployeeName" value="${currentName}" 
                                                   class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500">
                                        </div>
                                        <div class="mb-4">
                                            <label class="block text-sm font-medium text-gray-700">Email</label>
                                            <input type="email" id="editEmployeeEmail" value="${currentEmail}" 
                                                   class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500">
                                        </div>
                                        <div class="mb-4">
                                            <label class="block text-sm font-medium text-gray-700">Phone</label>
                                            <input type="tel" id="editEmployeePhone" value="${currentPhone}" 
                                                   class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500">
                                        </div>
                                        <div class="mb-4">
                                            <label class="block text-sm font-medium text-gray-700">New Password (leave blank to keep current)</label>
                                            <input type="password" id="editEmployeePassword" placeholder="Enter new password (optional)" 
                                                   class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500">
                                        </div>
                                    </form>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
                        <button type="button" onclick="updateEmployeeSuper(${employeeId})" 
                                class="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-indigo-600 text-base font-medium text-white hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:ml-3 sm:w-auto sm:text-sm">
                            Update Employee
                        </button>
                        <button type="button" onclick="closeEditEmployeeModal()" 
                                class="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm">
                            Cancel
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Add modal to body
    document.body.insertAdjacentHTML('beforeend', modalHTML);
}

// DOWNLOAD REPORT FUNCTION
async function downloadReport() {
    try {
        const response = await fetch('/superadmin/download-report', {
            method: 'GET',
            credentials: 'include'
        });
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            a.download = `system_transactions_${new Date().toISOString().split('T')[0]}.pdf`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } else {
            const errorData = await response.json();
            alert(`Error: ${errorData.error}`);
        }
    } catch (error) {
        console.error('Error downloading report:', error);
        alert('Error downloading report');
    }
}