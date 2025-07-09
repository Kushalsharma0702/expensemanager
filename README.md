# Expense Management Platform

A complete expense management system with three user roles: SuperAdmin, Admin, and Employee.

## Features

### SuperAdmin
- Allocate budgets to admins
- View budget overview with charts
- Monitor spending across all admins

### Admin
- View and approve/reject employee expense requests
- Monitor personal budget allocation and spending
- Visual budget tracking with charts

### Employee
- Submit expense requests to admins
- Track status of submitted requests
- View history of all expense submissions

## Tech Stack

- **Backend**: Python Flask with SQLAlchemy
- **Database**: PostgreSQL
- **Frontend**: HTML, CSS (Tailwind), JavaScript, Chart.js
- **Authentication**: Flask-Login with session cookies

## Quick Start

### Prerequisites
- Python 3.8+
- PostgreSQL
- pip

### Installation

1. Clone the repository and navigate to the project folder:
```bash
cd expense_platform
```

2. Install Python dependencies:
```bash
cd backend
pip install -r requirements.txt
```

3. Set up PostgreSQL database:
```bash
# Create database and run the SQL script
psql -U postgres -f ../database_setup.sql
```

4. Update database connection in `.env`:
```
DATABASE_URL=postgresql://username:password@localhost/expense_platform
SECRET_KEY=your-secret-key-here
```

5. Start the Flask application:
```bash
python app.py
```

6. Open your browser and go to `http://localhost:5000`

## Demo Accounts

| Role | Email | Password |
|------|-------|----------|
| SuperAdmin | superadmin@example.com | test123 |
| Admin | admin1@example.com | test123 |
| Admin | admin2@example.com | test123 |
| Employee | emp1@example.com | test123 |
| Employee | emp2@example.com | test123 |

## API Endpoints

### Authentication
- `POST /auth/login` - User login
- `POST /auth/logout` - User logout
- `GET /auth/me` - Get current user info

### SuperAdmin
- `POST /superadmin/allocate` - Allocate budget to admin
- `GET /superadmin/overview` - Get budget overview
- `GET /superadmin/admins` - Get all admins

### Admin
- `GET /admin/expenses` - Get pending expense requests
- `POST /admin/approve` - Approve expense request
- `POST /admin/reject` - Reject expense request
- `GET /admin/budget` - Get personal budget info

### Employee
- `POST /employee/submit` - Submit expense request
- `GET /employee/myrequests` - Get personal expense requests
- `GET /employee/admins` - Get all admins

## Testing with cURL

### Login
```bash
curl -X POST http://localhost:5000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"superadmin@example.com","password":"test123"}' \
  -c cookies.txt
```

### Get Budget Overview (SuperAdmin)
```bash
curl -X GET http://localhost:5000/superadmin/overview \
  -b cookies.txt
```

### Allocate Budget (SuperAdmin)
```bash
curl -X POST http://localhost:5000/superadmin/allocate \
  -H "Content-Type: application/json" \
  -d '{"admin_id":2,"amount":5000}' \
  -b cookies.txt
```

### Submit Expense (Employee)
```bash
curl -X POST http://localhost:5000/employee/submit \
  -H "Content-Type: application/json" \
  -d '{"admin_id":2,"amount":250,"reason":"Office supplies"}' \
  -b cookies.txt
```

### Get Pending Expenses (Admin)
```bash
curl -X GET http://localhost:5000/admin/expenses \
  -b cookies.txt
```

### Approve Expense (Admin)
```bash
curl -X POST http://localhost:5000/admin/approve \
  -H "Content-Type: application/json" \
  -d '{"expense_id":1}' \
  -b cookies.txt
```

## Password Hashing

To generate password hashes for new users:

```python
from werkzeug.security import generate_password_hash
hashed = generate_password_hash('your_password')
print(hashed)
```

## Project Structure

```
expense_platform/
├── backend/
│   ├── app.py              # Main Flask application
│   ├── extensions.py       # Flask extensions
│   ├── models.py          # Database models
│   ├── routes/
│   │   ├── auth.py        # Authentication routes
│   │   ├── superadmin.py  # SuperAdmin routes
│   │   ├── admin.py       # Admin routes
│   │   └── employee.py    # Employee routes
│   ├── .env               # Environment variables
│   └── requirements.txt   # Python dependencies
├── frontend/
│   ├── login.html         # Login page
│   ├── dashboard_superadmin.html
│   ├── dashboard_admin.html
│   ├── dashboard_employee.html
│   └── js/
│       ├── login.js
│       ├── superadmin.js
│       ├── admin.js
│       └── employee.js
├── database_setup.sql     # Database schema and demo data
└── README.md             # This file
```

## Security Features

- Password hashing with Werkzeug
- Session-based authentication with Flask-Login
- Role-based access control
- CSRF protection with proper CORS setup
- Input validation and sanitization

## Production Deployment

For production deployment:

1. Set strong secret key in `.env`
2. Use production PostgreSQL database
3. Enable HTTPS
4. Set up proper logging
5. Use a production WSGI server like Gunicorn
6. Consider using Redis for session storage

## Support

For issues or questions, please check the code comments and API documentation in the route files.