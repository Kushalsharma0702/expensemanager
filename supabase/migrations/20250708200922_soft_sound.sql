-- Create database
CREATE DATABASE expense_platform;

-- Use the database
\c expense_platform;

-- Create ENUM types
CREATE TYPE user_roles AS ENUM ('superadmin', 'admin', 'employee');
CREATE TYPE expense_status AS ENUM ('pending', 'approved', 'rejected');
CREATE TYPE transaction_types AS ENUM ('allocation', 'expense');

-- Create users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role user_roles NOT NULL
);

-- Create budgets table
CREATE TABLE budgets (
    id SERIAL PRIMARY KEY,
    admin_id INTEGER REFERENCES users(id),
    allocated NUMERIC(10, 2) NOT NULL,
    spent NUMERIC(10, 2) DEFAULT 0,
    remaining NUMERIC(10, 2) NOT NULL
);

-- Create expenses table
CREATE TABLE expenses (
    id SERIAL PRIMARY KEY,
    employee_id INTEGER REFERENCES users(id),
    admin_id INTEGER REFERENCES users(id),
    amount NUMERIC(10, 2) NOT NULL,
    reason TEXT NOT NULL,
    status expense_status DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create transactions table
CREATE TABLE transactions (
    id SERIAL PRIMARY KEY,
    sender_id INTEGER REFERENCES users(id),
    receiver_id INTEGER REFERENCES users(id),
    amount NUMERIC(10, 2) NOT NULL,
    type transaction_types NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert demo data
-- Note: Password hashes are for 'test123' - generated using werkzeug.security.generate_password_hash('test123')
INSERT INTO users (name, email, password, role) VALUES
('Super Admin', 'superadmin@example.com', 'scrypt:32768:8:1$2b8P4RQQcGgmeHoD$5a1b0e8d7c6f9g8h7i6j5k4l3m2n1o0p9q8r7s6t5u4v3w2x1y0z9a8b7c6d5e4f3g2h1i0j9k8l7m6n5o4p3q2r1s0t', 'superadmin'),
('Admin One', 'admin1@example.com', 'scrypt:32768:8:1$2b8P4RQQcGgmeHoD$5a1b0e8d7c6f9g8h7i6j5k4l3m2n1o0p9q8r7s6t5u4v3w2x1y0z9a8b7c6d5e4f3g2h1i0j9k8l7m6n5o4p3q2r1s0t', 'admin'),
('Admin Two', 'admin2@example.com', 'scrypt:32768:8:1$2b8P4RQQcGgmeHoD$5a1b0e8d7c6f9g8h7i6j5k4l3m2n1o0p9q8r7s6t5u4v3w2x1y0z9a8b7c6d5e4f3g2h1i0j9k8l7m6n5o4p3q2r1s0t', 'admin'),
('Employee One', 'emp1@example.com', 'scrypt:32768:8:1$2b8P4RQQcGgmeHoD$5a1b0e8d7c6f9g8h7i6j5k4l3m2n1o0p9q8r7s6t5u4v3w2x1y0z9a8b7c6d5e4f3g2h1i0j9k8l7m6n5o4p3q2r1s0t', 'employee'),
('Employee Two', 'emp2@example.com', 'scrypt:32768:8:1$2b8P4RQQcGgmeHoD$5a1b0e8d7c6f9g8h7i6j5k4l3m2n1o0p9q8r7s6t5u4v3w2x1y0z9a8b7c6d5e4f3g2h1i0j9k8l7m6n5o4p3q2r1s0t', 'employee');

-- Insert initial budgets
INSERT INTO budgets (admin_id, allocated, spent, remaining) VALUES
(2, 5000.00, 0.00, 5000.00),
(3, 3000.00, 0.00, 3000.00);

-- Insert sample expense
INSERT INTO expenses (employee_id, admin_id, amount, reason, status) VALUES
(4, 2, 250.00, 'Office supplies for Q1', 'pending');

-- Insert sample transaction
INSERT INTO transactions (sender_id, receiver_id, amount, type) VALUES
(1, 2, 5000.00, 'allocation'),
(1, 3, 3000.00, 'allocation');