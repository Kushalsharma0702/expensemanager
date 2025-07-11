-- Drop and recreate the public schema
DROP SCHEMA IF EXISTS public CASCADE;
CREATE SCHEMA public;

-- Enum types
CREATE TYPE user_roles AS ENUM ('superadmin', 'admin', 'employee');
CREATE TYPE expense_status AS ENUM ('pending', 'approved', 'rejected');
CREATE TYPE transaction_type AS ENUM ('allocation', 'expense', 'refund');

-- Table: users
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    phone VARCHAR(20),
    password TEXT NOT NULL,
    role user_roles NOT NULL,
    created_by INTEGER REFERENCES users(id),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes on users
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_created_by ON users(created_by);
CREATE INDEX idx_users_is_active ON users(is_active);

-- Table: budgets
CREATE TABLE budgets (
    id SERIAL PRIMARY KEY,
    admin_id INTEGER NOT NULL REFERENCES users(id),
    allocated NUMERIC(15, 2) NOT NULL DEFAULT 0,
    spent NUMERIC(15, 2) NOT NULL DEFAULT 0,
    remaining NUMERIC(15, 2) NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index on budgets
CREATE INDEX idx_budgets_admin_id ON budgets(admin_id);

-- Table: employee_funds
CREATE TABLE employee_funds (
    id SERIAL PRIMARY KEY,
    employee_id INTEGER NOT NULL REFERENCES users(id),
    admin_id INTEGER NOT NULL REFERENCES users(id),
    allocated NUMERIC(15, 2) NOT NULL DEFAULT 0,
    spent NUMERIC(15, 2) NOT NULL DEFAULT 0,
    remaining NUMERIC(15, 2) NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes on employee_funds
CREATE INDEX idx_employee_funds_employee_id ON employee_funds(employee_id);
CREATE INDEX idx_employee_funds_admin_id ON employee_funds(admin_id);
CREATE INDEX idx_employee_funds_composite ON employee_funds(employee_id, admin_id);

-- Table: expenses
CREATE TABLE expenses (
    id SERIAL PRIMARY KEY,
    employee_id INTEGER NOT NULL REFERENCES users(id),
    admin_id INTEGER NOT NULL REFERENCES users(id),
    amount NUMERIC(15, 2) NOT NULL,
    reason TEXT NOT NULL,
    status expense_status NOT NULL DEFAULT 'pending',
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reviewed_at TIMESTAMP,
    reviewer_comments TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes on expenses
CREATE INDEX idx_expenses_employee_id ON expenses(employee_id);
CREATE INDEX idx_expenses_admin_id ON expenses(admin_id);
CREATE INDEX idx_expenses_status ON expenses(status);
CREATE INDEX idx_expenses_composite ON expenses(employee_id, status);

-- Table: transactions
CREATE TABLE transactions (
    id SERIAL PRIMARY KEY,
    sender_id INTEGER REFERENCES users(id),
    receiver_id INTEGER REFERENCES users(id),
    expense_id INTEGER REFERENCES expenses(id),
    type transaction_type NOT NULL,
    amount NUMERIC(15, 2) NOT NULL,
    description TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes on transactions
CREATE INDEX idx_transactions_sender_id ON transactions(sender_id);
CREATE INDEX idx_transactions_receiver_id ON transactions(receiver_id);
CREATE INDEX idx_transactions_expense_id ON transactions(expense_id);
CREATE INDEX idx_transactions_type ON transactions(type);
CREATE INDEX idx_transactions_timestamp ON transactions(timestamp);
CREATE INDEX idx_transactions_created_at ON transactions(created_at);
CREATE INDEX idx_transactions_composite ON transactions(sender_id, type, created_at);
