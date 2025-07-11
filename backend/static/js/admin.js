// Session check - runs first
document.addEventListener('DOMContentLoaded', async function() {
    const res = await fetch('/auth/check-session', { credentials: 'include' });
    if (res.status !== 200) {
        window.location.href = '/';
        return;
    }
});

// Chart variables
let budgetChart, employeeChart;

// AI Insights Charts
let spendingTrendChart, employeePerformanceChart, dayPatternsChart;

// Main DOMContentLoaded event - runs once
document.addEventListener('DOMContentLoaded', function() {
    // Initialize dashboard
    loadUserInfo();
    loadDashboard();
    loadPendingExpenses();
    loadEmployeeStats();
    loadReports();
    loadEmployeeTransactions();
    populateExpenseEmployeeSelect();
    populateAllocateEmployeeSelect();
    
    // LOGOUT FUNCTIONALITY - CRITICAL FIX
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

    // ADD EXPENSE FORM HANDLER
    const addExpenseForm = document.getElementById('addExpenseForm');
    if (addExpenseForm) {
        addExpenseForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const employee_id = parseInt(document.getElementById('expenseEmployeeSelect').value);
            const amount = parseFloat(document.getElementById('expenseAmount').value);
            const reason = document.getElementById('expenseReason').value.trim();
            
            if (!employee_id || !amount || !reason) {
                showToast('All fields are required', 'error');
                return;
            }
            
            try {
                const response = await fetch('/admin/add-expense', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ employee_id, amount, reason }),
                    credentials: 'include'
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    showToast('Expense added successfully!', 'success');
                    this.reset();
                    loadDashboard();
                    loadEmployeeStats();
                    loadEmployeeTransactions();
                } else {
                    showToast(result.error || 'Failed to add expense', 'error');
                }
            } catch (error) {
                console.error('Error adding expense:', error);
                showToast('Error adding expense', 'error');
            }
        });
    }

    // ADD EMPLOYEE FORM HANDLER
    const addEmployeeForm = document.getElementById('addEmployeeForm');
    if (addEmployeeForm) {
        addEmployeeForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const name = document.getElementById('employeeName').value.trim();
            const email = document.getElementById('employeeEmail').value.trim();
            const phone = document.getElementById('employeePhone').value.trim();
            const password = document.getElementById('employeePassword').value.trim() || 'password';
            
            if (!name || !email || !phone) {
                showToast('Name, email, and phone are required', 'error');
                return;
            }
            
            try {
                const response = await fetch('/admin/add-employee', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name, email, phone, password }),
                    credentials: 'include'
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    showToast(`Employee added successfully! Password: ${password}`, 'success');
                    this.reset();
                    populateExpenseEmployeeSelect();
                    populateAllocateEmployeeSelect();
                    loadEmployeeStats();
                } else {
                    showToast(result.error || 'Failed to add employee', 'error');
                }
            } catch (error) {
                console.error('Error adding employee:', error);
                showToast('Error adding employee', 'error');
            }
        });
    }

    // ALLOCATE FUND FORM HANDLER
    const allocateFundForm = document.getElementById('allocateFundForm');
    if (allocateFundForm) {
        allocateFundForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const employee_id = parseInt(document.getElementById('allocateEmployeeSelect').value);
            const amount = parseFloat(document.getElementById('allocateAmount').value);
            
            if (!employee_id || !amount || amount <= 0) {
                showToast('Please select employee and enter valid amount', 'error');
                return;
            }
            
            try {
                const response = await fetch('/admin/allocate-fund', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ employee_id, amount }),
                    credentials: 'include'
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    showToast('Fund allocated successfully!', 'success');
                    this.reset();
                    loadDashboard();
                    loadEmployeeStats();
                } else {
                    showToast(result.error || 'Failed to allocate fund', 'error');
                }
            } catch (error) {
                console.error('Error allocating fund:', error);
                showToast('Error allocating fund', 'error');
            }
        });
    }

    // DOWNLOAD PDF BUTTON
    const downloadBtn = document.getElementById('downloadTransactionsPdf');
    if (downloadBtn) {
        downloadBtn.addEventListener('click', async function() {
            try {
                const res = await fetch('/admin/employee-transactions-pdf', { 
                    method: 'GET', 
                    credentials: 'include' 
                });
                
                if (res.ok) {
                    const blob = await res.blob();
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'employee_transactions.pdf';
                    document.body.appendChild(a);
                    a.click();
                    a.remove();
                    window.URL.revokeObjectURL(url);
                    showToast('PDF downloaded successfully!', 'success');
                } else {
                    showToast('Failed to generate PDF', 'error');
                }
            } catch (error) {
                console.error('PDF download error:', error);
                showToast('Error downloading PDF', 'error');
            }
        });
    }

    // AI insights
    loadAIInsights();
    
    // Refresh AI insights every 5 minutes
    setInterval(loadAIInsights, 300000);
});

// LOAD USER INFO
async function loadUserInfo() {
    try {
        const response = await fetch('/auth/me', { credentials: 'include' });
        if (response.ok) {
            const user = await response.json();
            const userNameElement = document.getElementById('userName');
            if (userNameElement) {
                userNameElement.textContent = user.name;
            }
        }
    } catch (error) {
        console.error('Error loading user info:', error);
    }
}

// LOAD DASHBOARD DATA
async function loadDashboard() {
    try {
        const response = await fetch('/admin/dashboard', { credentials: 'include' });
        if (response.ok) {
            const data = await response.json();
            updateDashboardCards(data);
            updateBudgetChart(data.budget);
        }
    } catch (error) {
        console.error('Error loading dashboard:', error);
    }
}

// UPDATE DASHBOARD CARDS
function updateDashboardCards(data) {
    const totalBudgetEl = document.getElementById('totalBudget');
    const totalSpentEl = document.getElementById('totalSpent');
    const remainingEl = document.getElementById('remaining');
    const pendingCountEl = document.getElementById('pendingCount');

    if (totalBudgetEl) totalBudgetEl.textContent = `₹${data.budget.total_budget.toFixed(2)}`;
    if (totalSpentEl) totalSpentEl.textContent = `₹${data.budget.total_spent.toFixed(2)}`;
    if (remainingEl) remainingEl.textContent = `₹${data.budget.remaining.toFixed(2)}`;
    if (pendingCountEl) pendingCountEl.textContent = data.pending_count;
}

// LOAD PENDING EXPENSES
async function loadPendingExpenses() {
    try {
        const response = await fetch('/admin/expenses', { credentials: 'include' });
        if (response.ok) {
            const data = await response.json();
            updatePendingExpenses(data.expenses);
        }
    } catch (error) {
        console.error('Error loading expenses:', error);
    }
}

// UPDATE PENDING EXPENSES TABLE
function updatePendingExpenses(expenses) {
    const tbody = document.getElementById('pendingExpensesBody');
    if (!tbody) return;
    
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

// APPROVE EXPENSE
async function approveExpense(expenseId) {
    if (!confirm('Approve this expense?')) return;
    
    try {
        const response = await fetch(`/admin/approve-expense/${expenseId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include'
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showToast('Expense approved successfully!', 'success');
            loadDashboard();
            loadPendingExpenses();
            loadEmployeeStats();
        } else {
            showToast(result.error || 'Failed to approve expense', 'error');
        }
    } catch (error) {
        console.error('Error approving expense:', error);
        showToast('Error approving expense', 'error');
    }
}

// REJECT EXPENSE
async function rejectExpense(expenseId) {
    if (!confirm('Reject this expense?')) return;
    
    try {
        const response = await fetch(`/admin/reject-expense/${expenseId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include'
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showToast('Expense rejected successfully!', 'success');
            loadDashboard();
            loadPendingExpenses();
        } else {
            showToast(result.error || 'Failed to reject expense', 'error');
        }
    } catch (error) {
        console.error('Error rejecting expense:', error);
        showToast('Error rejecting expense', 'error');
    }
}

// POPULATE EMPLOYEE SELECT FOR EXPENSE
async function populateExpenseEmployeeSelect() {
    const select = document.getElementById('expenseEmployeeSelect');
    if (!select) return;
    
    select.innerHTML = '<option value="">Loading...</option>';
    try {
        const res = await fetch('/admin/employees', { credentials: 'include' });
        if (res.ok) {
            const data = await res.json();
            select.innerHTML = '<option value="">Select employee...</option>';
            data.employees.forEach(emp => {
                const option = document.createElement('option');
                option.value = emp.id;
                option.textContent = `${emp.name} (${emp.email})`;
                select.appendChild(option);
            });
        } else {
            select.innerHTML = '<option value="">No employees found</option>';
        }
    } catch {
        select.innerHTML = '<option value="">Error loading employees</option>';
    }
}

// POPULATE EMPLOYEE SELECT FOR ALLOCATION
async function populateAllocateEmployeeSelect() {
    const select = document.getElementById('allocateEmployeeSelect');
    if (!select) return;
    
    select.innerHTML = '<option value="">Loading...</option>';
    try {
        const res = await fetch('/admin/employees', { credentials: 'include' });
        if (res.ok) {
            const data = await res.json();
            select.innerHTML = '<option value="">Select employee...</option>';
            data.employees.forEach(emp => {
                const option = document.createElement('option');
                option.value = emp.id;
                option.textContent = `${emp.name} (${emp.email})`;
                select.appendChild(option);
            });
        } else {
            select.innerHTML = '<option value="">No employees found</option>';
        }
    } catch {
        select.innerHTML = '<option value="">Error loading employees</option>';
    }
}

// LOAD EMPLOYEE STATS
async function loadEmployeeStats() {
    try {
        const response = await fetch('/admin/employee-stats', { credentials: 'include' });
        if (response.ok) {
            const data = await response.json();
            updateEmployeeStats(data.employees);      // <-- Table
            updateEmployeeChart(data.employees);      // <-- Chart
        }
    } catch (error) {
        console.error('Error loading employee stats:', error);
    }
}

// UPDATE EMPLOYEE STATS TABLE
function updateEmployeeStats(employees) {
    const tbody = document.getElementById('employeeStatsBody');
    if (!tbody) return;

    tbody.innerHTML = '';

    if (!employees || employees.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="px-6 py-4 text-center text-gray-500">
                    No employee statistics available
                </td>
            </tr>
        `;
        return;
    }

    employees.forEach(emp => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td class="px-6 py-4 whitespace-nowrap">
                <div class="text-sm font-medium text-gray-900">${emp.name}</div>
                <div class="text-sm text-gray-500">${emp.email}</div>
                <div class="text-sm text-gray-400">${emp.phone || 'No phone'}</div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${emp.total_requests}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">₹${emp.total_amount.toFixed(2)}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-green-700">${emp.approved}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-yellow-700">${emp.pending}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-red-700">${emp.rejected}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm font-medium">
                <button onclick="editEmployee(${emp.id}, '${emp.name}', '${emp.email}', '${emp.phone || ''}')" 
                        class="text-indigo-600 hover:text-indigo-900 mr-3">
                    <i class="fas fa-edit"></i> Edit
                </button>
            </td>
        `;
        tbody.appendChild(row);
    });
}

// UPDATE EMPLOYEE CHART
function updateEmployeeChart(employees) {
    const ctx = document.getElementById('employeeChart');
    if (!ctx) return;

    if (window.employeeChartInstance) {
        window.employeeChartInstance.destroy();
    }

    if (!employees || employees.length === 0) {
        ctx.parentElement.innerHTML = '<div class="text-center text-gray-500 pt-12">No employee data available</div>';
        return;
    }

    // If all employees have zero total_amount and zero approved_amount, show message
    if (employees.every(e => (e.total_amount || 0) === 0 && (e.approved_amount || 0) === 0)) {
        ctx.parentElement.innerHTML = '<div class="text-center text-gray-500 pt-12">No employee spending data yet</div>';
        return;
    }

    window.employeeChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: employees.map(e => e.name),
            datasets: [
                {
                    label: 'Total Spent (₹)',
                    data: employees.map(e => e.total_amount || 0),
                    backgroundColor: 'rgba(59, 130, 246, 0.8)'
                },
                {
                    label: 'Approved Spent (₹)',
                    data: employees.map(e => e.approved_amount || 0),
                    backgroundColor: 'rgba(16, 185, 129, 0.7)'
                },
                {
                    label: 'Total Requests',
                    data: employees.map(e => e.total_requests || 0),
                    backgroundColor: 'rgba(239, 68, 68, 0.5)',
                    type: 'line',
                    yAxisID: 'y1'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'bottom' },
                title: { display: false }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: { display: true, text: 'Amount (₹)' }
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    beginAtZero: true,
                    title: { display: true, text: 'Requests' },
                    grid: { drawOnChartArea: false }
                }
            }
        }
    });
}

// UPDATE BUDGET CHART
function updateBudgetChart(budget) {
    const ctx = document.getElementById('budgetChart');
    if (!ctx) return;

    if (window.budgetChartInstance) {
        window.budgetChartInstance.destroy();
    }

    window.budgetChartInstance = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Allocated to Employees', 'Remaining with Admin', 'Spent by Employees'],
            datasets: [{
                data: [
                    budget.total_spent || 0,      // Allocated to Employees
                    budget.remaining || 0,        // Remaining with Admin
                    budget.employee_spent || 0    // Spent by Employees
                ],
                backgroundColor: [
                    'rgba(59, 130, 246, 0.8)',   // blue
                    'rgba(16, 185, 129, 0.8)',   // green
                    'rgba(239, 68, 68, 0.8)'     // red
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'bottom' },
                title: { display: false }
            }
        }
    });
}

// LOAD EMPLOYEE TRANSACTIONS
async function loadEmployeeTransactions() {
    try {
        const res = await fetch('/admin/employee-transactions', { credentials: 'include' });
        if (res.ok) {
            const data = await res.json();
            const tbody = document.getElementById('employeeTransactionsBody');
            if (tbody) {
                tbody.innerHTML = '';
                if (data.transactions && data.transactions.length === 0) {
                    tbody.innerHTML = `<tr><td colspan="5" class="px-6 py-4 text-center text-gray-500">No transactions found</td></tr>`;
                    return;
                }
                if (data.transactions) {
                    data.transactions.forEach(tx => {
                        const row = document.createElement('tr');
                        row.innerHTML = `
                            <td class="px-6 py-4">${new Date(tx.date).toLocaleDateString()}</td>
                            <td class="px-6 py-4">${tx.employee_name}</td>
                            <td class="px-6 py-4">₹${tx.amount.toFixed(2)}</td>
                            <td class="px-6 py-4">${tx.type}</td>
                            <td class="px-6 py-4">${tx.description}</td>
                        `;
                        tbody.appendChild(row);
                    });
                }
            }
        }
    } catch (e) {
        console.error('Error loading transactions:', e);
    }
}

// LOAD REPORTS
async function loadReports() {
    try {
        const response = await fetch('/admin/reports', { credentials: 'include' });
        if (response.ok) {
            const data = await response.json();
            updateReportsDisplay(data.report_data);
        }
    } catch (error) {
        console.error('Error loading reports:', error);
    }
}

// UPDATE REPORTS DISPLAY
function updateReportsDisplay(reportData) {
    // Implementation for reports display
    console.log('Reports loaded:', reportData);
}

// EXPORT FUNCTIONS
async function exportPDF() {
    try {
        showToast('Generating PDF report...', 'info');
        
        const response = await fetch('/admin/export-pdf', {
            method: 'POST',
            credentials: 'include'
        });
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `admin_report_${new Date().toISOString().split('T')[0]}.pdf`;
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(url);
            
            showToast('PDF report downloaded successfully!', 'success');
        } else {
            showToast('Failed to generate PDF report', 'error');
        }
    } catch (error) {
        console.error('Error exporting PDF:', error);
        showToast('Error generating PDF report', 'error');
    }
}

async function exportExcel() {
    try {
        showToast('Generating Excel report...', 'info');
        
        const response = await fetch('/admin/export-excel', {
            method: 'POST',
            credentials: 'include'
        });
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `admin_report_${new Date().toISOString().split('T')[0]}.xlsx`;
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(url);
            
            showToast('Excel report downloaded successfully!', 'success');
        } else {
            showToast('Failed to generate Excel report', 'error');
        }
    } catch (error) {
        console.error('Error exporting Excel:', error);
        showToast('Error generating Excel report', 'error');
    }
}

// Load AI insights data
async function loadAIInsights() {
    try {
        const response = await fetch('/ai/admin/spending-trends', { credentials: 'include' });
        if (response.ok) {
            const data = await response.json();
            updateSpendingTrendChart(data.monthly_trends);
            updateEmployeePerformanceChart(data.employee_insights);
            updateDayPatternsChart(data.day_patterns);
            displayAIInsights(data.insights);
        }
    } catch (error) {
        console.error('Error loading AI insights:', error);
    }
}

function updateSpendingTrendChart(monthlyData) {
    const ctx = document.getElementById('spendingTrendChart');
    if (!ctx) return;

    if (spendingTrendChart) {
        spendingTrendChart.destroy();
    }

    spendingTrendChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: monthlyData.map(d => d.period),
            datasets: [
                {
                    label: 'Total Spent (₹)',
                    data: monthlyData.map(d => d.total_spent),
                    borderColor: 'rgb(59, 130, 246)',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    tension: 0.4,
                    fill: true
                },
                {
                    label: 'Expense Count',
                    data: monthlyData.map(d => d.expense_count),
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
                    text: 'Monthly Spending Trends'
                },
                legend: {
                    display: true
                }
            },
            scales: {
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
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
                        text: 'Count'
                    },
                    grid: {
                        drawOnChartArea: false,
                    },
                }
            }
        }
    });
}

function updateEmployeePerformanceChart(employeeData) {
    const ctx = document.getElementById('employeePerformanceChart');
    if (!ctx) return;

    if (employeePerformanceChart) {
        employeePerformanceChart.destroy();
    }

    // Sort by efficiency score
    employeeData.sort((a, b) => b.efficiency_score - a.efficiency_score);

    employeePerformanceChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: employeeData.map(emp => emp.name),
            datasets: [
                {
                    label: 'Total Spent (₹)',
                    data: employeeData.map(emp => emp.total_spent),
                    backgroundColor: 'rgba(59, 130, 246, 0.8)',
                    borderColor: 'rgb(59, 130, 246)',
                    borderWidth: 1
                },
                {
                    label: 'Efficiency Score',
                    data: employeeData.map(emp => emp.efficiency_score),
                    backgroundColor: 'rgba(34, 197, 94, 0.8)',
                    borderColor: 'rgb(34, 197, 94)',
                    borderWidth: 1,
                    yAxisID: 'y1'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'Employee Performance Analysis'
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Amount (₹)'
                    }
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    beginAtZero: true,
                    max: 100,
                    title: {
                        display: true,
                        text: 'Efficiency Score'
                    },
                    grid: {
                        drawOnChartArea: false,
                    }
                }
            }
        }
    });
}

function updateDayPatternsChart(dayData) {
    const ctx = document.getElementById('dayPatternsChart');
    if (!ctx) return;

    if (dayPatternsChart) {
        dayPatternsChart.destroy();
    }

    dayPatternsChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: dayData.map(d => d.day),
            datasets: [{
                data: dayData.map(d => d.total_amount),
                backgroundColor: [
                    '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0',
                    '#9966FF', '#FF9F40', '#FF6384'
                ],
                hoverOffset: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'Spending by Day of Week'
                },
                legend: {
                    position: 'bottom'
                }
            }
        }
    });
}

function displayAIInsights(insights) {
    const container = document.getElementById('aiInsightsContainer');
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

function getInsightClasses(type) {
    const classes = {
        'success': 'bg-green-50 border-green-400 text-green-800',
        'warning': 'bg-yellow-50 border-yellow-400 text-yellow-800',
        'error': 'bg-red-50 border-red-400 text-red-800',
        'info': 'bg-blue-50 border-blue-400 text-blue-800'
    };
    return classes[type] || classes.info;
}

function getInsightIcon(type) {
    const icons = {
        'success': '<i class="fas fa-check-circle text-green-500"></i>',
        'warning': '<i class="fas fa-exclamation-triangle text-yellow-500"></i>',
        'error': '<i class="fas fa-exclamation-circle text-red-500"></i>',
        'info': '<i class="fas fa-info-circle text-blue-500"></i>'
    };
    return icons[type] || icons.info;
}

// EDIT EMPLOYEE FUNCTION
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
                        <button type="button" onclick="updateEmployee(${employeeId})" 
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

// UPDATE EMPLOYEE FUNCTION
async function updateEmployee(employeeId) {
    const name = document.getElementById('editEmployeeName').value.trim();
    const email = document.getElementById('editEmployeeEmail').value.trim();
    const phone = document.getElementById('editEmployeePhone').value.trim();
    const password = document.getElementById('editEmployeePassword').value.trim();
    
    if (!name || !email || !phone) {
        showToast('Name, email, and phone are required', 'error');
        return;
    }
    
    try {
        const requestBody = {
            employee_id: employeeId,
            name: name,
            email: email,
            phone: phone
        };
        
        if (password) {
            requestBody.password = password;
        }
        
        const response = await fetch('/admin/edit-employee', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestBody),
            credentials: 'include'
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showToast('Employee updated successfully!', 'success');
            closeEditEmployeeModal();
            loadEmployeeStats();
            populateExpenseEmployeeSelect();
            populateAllocateEmployeeSelect();
        } else {
            showToast(result.error || 'Failed to update employee', 'error');
        }
    } catch (error) {
        console.error('Error updating employee:', error);
        showToast('Error updating employee', 'error');
    }
}

// CLOSE EDIT EMPLOYEE MODAL
function closeEditEmployeeModal() {
    const modal = document.getElementById('editEmployeeModal');
    if (modal) {
        modal.remove();
    }
}