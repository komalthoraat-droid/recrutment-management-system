# Recruitment & Placement Management System

A modular Python and MySQL backend for managing candidate recruitment and placement workflows. The backend uses a console menu; the separate HTML/CSS prototype is static and is not connected to Python or MySQL.

## Features

- Candidate and company registration, search, validation, and status management
- Job creation, status management, and required-skill configuration
- Eligibility checks for profile/job/company status, qualification, percentage, passing year, backlog count, application deadline, and required skills
- Duplicate application prevention and application history
- Shortlisting, interview rounds, interview feedback, and selection
- Offer creation and status tracking
- Placement registration and joining status
- Candidate, application, job, and placement reports
- Parameterized MySQL queries, transactional workflow updates, custom exceptions, and file activity logging

The code is organized as `model -> service -> DAO -> MySQL`, with console input and output in `rpms/app/main.py`.

## Static UI prototype

The standalone prototype is in [ui-prototype/](./ui-prototype/). Open `ui-prototype/login.html` in a browser to start, then use the sidebar links to navigate among the login, dashboard, candidate, company, job, application, interview, placement, and report screens. It uses hardcoded sample content; forms and filters do not save or retrieve data and there is no backend integration.

## Setup

1. Create and activate a virtual environment, then install the connector:

   ```powershell
   py -m venv .venv
   .venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

2. Create and seed the database. The schema script drops and recreates `recruitment_portal`, so use it only when that reset is intended:

   ```powershell
   mysql -u root -p -e "source sql/rpms_schema.sql"
   mysql -u root -p -e "source sql/rpms_sample_data.sql"
   ```

   `rpms_sample_data.sql` supplies demo users, including user ID `1`, which is the default actor recorded for workflow history.

3. Configure the database in the current PowerShell session. `RPMS_DB_PASSWORD` is empty by default:

   ```powershell
   $env:RPMS_DB_HOST = "localhost"
   $env:RPMS_DB_PORT = "3306"
   $env:RPMS_DB_USER = "root"
   $env:RPMS_DB_PASSWORD = "your-mysql-password"
   $env:RPMS_DB_NAME = "recruitment_portal"
   $env:RPMS_ACTOR_USER_ID = "1"
   ```

4. Start the application:

   ```powershell
   python main.py
   ```

`RPMS_ACTOR_USER_ID` must refer to a row in the database `users` table. Set the other `RPMS_DB_*` variables to match your MySQL installation.

## Tests

The service and eligibility tests do not require a running MySQL server:

```powershell
.venv\Scripts\python -m unittest discover -s tests
```
