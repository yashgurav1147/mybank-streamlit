# 🏦 MyBank — Streamlit Banking Management System

A beginner-friendly banking management application built with **Python + Streamlit + JSON**.

> **Portfolio/demo project:** This application is designed for learning and demonstration. It is not intended to handle real banking or financial information.

## 🚀 Live Demo

**Streamlit App:** Add your deployed Streamlit URL here

## 💻 GitHub

**Repository:** Add your GitHub repository URL here

## ✨ Features

- 🆕 Create a bank account
- 🔢 Generate a unique 10-digit account number
- 🔐 4-digit PIN authentication
- 💰 Deposit money
- 💸 Withdraw money
- 👤 View account details
- ✏️ Update name, email and PIN
- 🗑️ Delete an account
- 📊 Dashboard with account/transaction statistics
- 📜 Recent transaction history
- 💾 JSON-based local data storage
- 🔒 Salted PBKDF2-HMAC PIN hashing for new accounts
- 🔄 Backward compatibility with the original plaintext-PIN data format

## 🛠️ Tech Stack

| Technology | Purpose |
|---|---|
| Python | Application logic |
| Streamlit | Web interface |
| JSON | Local demo data storage |
| hashlib / hmac | PIN hashing and verification |
| secrets | Secure account-number / salt generation |

## 📁 Project Structure

```text
mybank-streamlit/
│
├── app.py
├── requirements.txt
├── README.md
├── .gitignore
└── data.json              # created locally, intentionally ignored by Git
```

## ▶️ Run Locally

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/mybank-streamlit.git
cd mybank-streamlit
```

### 2. Create a virtual environment

Windows:

```bash
python -m venv .venv
.venv\Scripts\activate
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Start Streamlit

```bash
streamlit run app.py
```

The application will open in your browser.

## ☁️ Deployment

This project can be deployed using **Streamlit Community Cloud**.

1. Push the repository to GitHub.
2. Sign in to Streamlit Community Cloud using GitHub.
3. Select the repository.
4. Select the `main` branch.
5. Set the main file to `app.py`.
6. Deploy the application.
7. Add the resulting `streamlit.app` URL to the README.

## ⚠️ Data Persistence

The project intentionally uses a local JSON file because the goal is to demonstrate Python classes, file handling, authentication, validation, and Streamlit UI.

On Streamlit Community Cloud, files generated while the application is running are **not guaranteed to persist**. Therefore, account creation and transaction data should be treated as temporary demo data.

For a production-style version, replace JSON storage with a persistent database such as PostgreSQL/Supabase.

## 🔐 Security Note

New accounts use salted PBKDF2-HMAC-SHA256 PIN hashing. This improves the project compared with storing PINs directly, but a 4-digit PIN still has a very small possible keyspace.

Do not use this project for real financial accounts or real customer information.

## 📚 Learning Goals

This project demonstrates:

- Object-oriented programming
- Classes and methods
- JSON file handling
- CRUD operations
- Input validation
- Authentication concepts
- PIN hashing
- Session state
- Streamlit forms and UI
- Basic software project structure
- Git and GitHub deployment workflow

## 🔮 Future Improvements

- Replace JSON with PostgreSQL/Supabase
- Add user registration/login with stronger authentication
- Add OTP/email verification
- Add account statements
- Add transfer functionality
- Add charts for transaction history
- Add automated tests
- Add CI/CD with GitHub Actions
