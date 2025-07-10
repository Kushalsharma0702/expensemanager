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
            
            if (!name || !email) {
                showToast('Name and email are required', 'error');
                return;
            }
            
            try {
                const response = await fetch('/admin/add-employee', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name, email, password: 'password' }),
                    credentials: 'include'
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    showToast('Employee added successfully! Default password: password', 'success');
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
        const response = await fetch('/admin/approve', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ expense_id: expenseId }),
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
        const response = await fetch('/admin/reject', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ expense_id: expenseId }),
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
            updateEmployeeStats(data.employees);
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

// UPDATE BUDGET CHART
function updateBudgetChart(budget) {
    // Implementation for budget chart
    console.log('Budget chart updated:', budget);
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