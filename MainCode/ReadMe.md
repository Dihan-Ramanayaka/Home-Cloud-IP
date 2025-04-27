# Home Cloud

Home Cloud is a lightweight, feature-rich cloud storage solution built with Flask. It allows users to upload, download, and manage files while providing an admin interface for managing users and storage limits. The application is designed to be simple, secure, and scalable.

---

## Features

### User Features
- **File Management**:
  - Upload, download, rename, and delete files.
  - Drag-and-drop file uploads.
  - Bulk file downloads as a ZIP archive.
- **Storage Management**:
  - View storage usage with a progress bar.
  - Request additional storage from the admin.
- **Pricing Plans**:
  - Choose from multiple storage plans (Free, Basic, Pro, Enterprise).
- **File Sharing**:
  - Generate shareable links for files.

### Admin Features
- **User Management**:
  - View all users and their storage usage.
  - Reset user passwords.
  - Delete all files for a specific user.
  - Suspend or delete user accounts.
- **Storage Management**:
  - Grant additional storage to users.
  - Approve user requests for storage upgrades.
- **Analytics**:
  - View detailed user statistics (e.g., total files, storage usage, last login).

### Security Features
- **Password Hashing**:
  - User passwords are securely hashed using `bcrypt`.
- **CSRF Protection**:
  - All forms are protected against CSRF attacks.
- **Rate Limiting**:
  - Prevent abuse of endpoints with rate limiting.

---

## Installation

### Prerequisites
- Python 3.10 or higher
- Flask and required dependencies
- Windows 10 22H2 Or Grater
- Wifi Connection
- 4GB Ram Or Grater
- Intergrated Graphics Or Grater
- Intel , AMD , Snapdragon CPU
- HDD , SDD , Flash Drive Storage
- Code Editor (ADVANCED)

### Steps
1. Clone the repository:
   ```bash
   git clone https://github.com/Diha/home-cloud.git
   cd home-cloud

2. Install Python Files
   ```bash
   pip install flask flask-bcrypt 

3. Run The Server 
    ```bash
    python sever.py

4. Acceess From Browser
    ```bash
    http://localhost:5000
