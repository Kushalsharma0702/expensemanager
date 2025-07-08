let budgetChart;

document.addEventListener('DOMContentLoaded', function() {
    loadUserInfo();
    loadAdmins();
    loadBudgetOverview();
    
    document.getElementById('allocateForm').addEventListener('submit', handleAllocate);
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
        const response = await fetch('/superadmin/admins', {
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

async function loadBudgetOverview() {
    try {
        const response = await fetch('/superadmin/overview', {
            credentials: 'include'
        });
        
        if (response.ok) {
            const data = await response.json();
            updateBudgetChart(data.budgets);
            updateBudgetTable(data.budgets);
        }
    } catch (error) {
        console.error('Error loading budget overview:', error);
    }
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
                            return '$' + value.toLocaleString();
                        }
                    }
                }
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return context.dataset.label + ': $' + context.parsed.y.toLocaleString();
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
    
    budgets.forEach(budget => {
        const usagePercent = budget.allocated > 0 ? (budget.spent / budget.allocated * 100).toFixed(1) : 0;
        const row = document.createElement('tr');
        row.innerHTML = `
            <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                ${budget.admin_name}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                $${budget.allocated.toLocaleString()}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                $${budget.spent.toLocaleString()}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                $${budget.remaining.toLocaleString()}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                <div class="flex items-center">
                    <div class="flex-1 bg-gray-200 rounded-full h-2 mr-2">
                        <div class="bg-blue-600 h-2 rounded-full" style="width: ${usagePercent}%"></div>
                    </div>
                    <span class="text-xs">${usagePercent}%</span>
                </div>
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
            loadBudgetOverview();
        } else {
            showMessage(result.error || 'Failed to allocate budget', 'error');
        }
    } catch (error) {
        showMessage('Error allocating budget', 'error');
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