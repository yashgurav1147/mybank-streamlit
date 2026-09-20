import json
import hashlib
import hmac
import secrets
import string
from pathlib import Path
from datetime import datetime

import streamlit as st


# ============================================================
# Configuration
# ============================================================

DATABASE = Path("data.json")
MAX_TRANSACTION = 10_000
PBKDF2_ITERATIONS = 200_000


# ============================================================
# Bank storage / business logic
# ============================================================

class Bank:
    def __init__(self, database: Path = DATABASE):
        self.database = database
        self.data = self._load()

    def _load(self):
        """Load accounts from JSON. Create an empty database if needed."""
        if not self.database.exists():
            return []

        try:
            with self.database.open("r", encoding="utf-8") as file:
                data = json.load(file)

            if not isinstance(data, list):
                raise ValueError("data.json must contain a list of accounts.")

            # Make sure older records also work with the new app.
            for account in data:
                account.setdefault("balance", 0)
                account.setdefault("transactions", [])

            return data

        except (json.JSONDecodeError, OSError, ValueError) as err:
            st.error(f"Could not read the database: {err}")
            return []

    def _save(self):
        """Save all account data back to JSON."""
        try:
            temp_file = self.database.with_suffix(".tmp")

            with temp_file.open("w", encoding="utf-8") as file:
                json.dump(self.data, file, indent=4)

            temp_file.replace(self.database)

        except OSError as err:
            raise RuntimeError(f"Could not save database: {err}") from err

    @staticmethod
    def _generate_account_number():
        """Generate a unique 10-digit account number."""
        return "".join(secrets.choice(string.digits) for _ in range(10))

    @staticmethod
    def _hash_pin(pin: str, salt: bytes | None = None):
        """Hash a PIN using PBKDF2-HMAC-SHA256."""
        if salt is None:
            salt = secrets.token_bytes(16)

        password = pin.encode("utf-8")
        derived_key = hashlib.pbkdf2_hmac(
            "sha256",
            password,
            salt,
            PBKDF2_ITERATIONS,
        )

        return salt.hex(), derived_key.hex()

    @classmethod
    def _verify_hashed_pin(cls, pin: str, account: dict) -> bool:
        """Verify a PIN for accounts using the new hashed format."""
        try:
            salt = bytes.fromhex(account["pin_salt"])
            _, expected_hash = cls._hash_pin(pin, salt)
            return hmac.compare_digest(expected_hash, account["pin_hash"])
        except (KeyError, ValueError):
            return False

    @classmethod
    def _verify_pin(cls, pin: str, account: dict) -> bool:
        """
        Verify both new hashed PINs and old PINs from the user's
        original JSON format.
        """
        if "pin_hash" in account and "pin_salt" in account:
            return cls._verify_hashed_pin(pin, account)

        # Backward compatibility for old data.json files.
        old_pin = str(account.get("pin", ""))
        return hmac.compare_digest(old_pin, pin)

    @classmethod
    def _upgrade_legacy_pin(cls, account: dict, pin: str):
        """Convert an old plaintext PIN into the new hashed format."""
        salt_hex, hash_hex = cls._hash_pin(pin)

        account["pin_salt"] = salt_hex
        account["pin_hash"] = hash_hex
        account.pop("pin", None)

    @staticmethod
    def _valid_pin(pin: str) -> bool:
        return pin.isdigit() and len(pin) == 4

    def authenticate(self, account_number: str, pin: str):
        """Return the matching account or None."""
        for account in self.data:
            if account.get("accountNo") == account_number:
                if self._verify_pin(pin, account):
                    # Automatically upgrade old accounts.
                    if "pin_hash" not in account:
                        self._upgrade_legacy_pin(account, pin)
                        self._save()
                    return account
                return None

        return None

    def account_exists(self, account_number: str) -> bool:
        return any(
            account.get("accountNo") == account_number
            for account in self.data
        )

    def create_account(self, name: str, age: int, email: str, pin: str):
        """Create and persist a new account."""
        account_number = self._generate_account_number()

        while self.account_exists(account_number):
            account_number = self._generate_account_number()

        pin_salt, pin_hash = self._hash_pin(pin)

        account = {
            "name": name.strip(),
            "age": age,
            "email": email.strip().lower(),
            "accountNo": account_number,
            "pin_salt": pin_salt,
            "pin_hash": pin_hash,
            "balance": 0,
            "transactions": [],
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        self.data.append(account)
        self._save()

        return account

    def deposit(self, account: dict, amount: int):
        if amount <= 0:
            raise ValueError("Deposit amount must be greater than 0.")

        if amount > MAX_TRANSACTION:
            raise ValueError(
                f"Maximum deposit per transaction is ₹{MAX_TRANSACTION:,}."
            )

        account["balance"] += amount
        self._add_transaction(account, "Deposit", amount)
        self._save()

    def withdraw(self, account: dict, amount: int):
        if amount <= 0:
            raise ValueError("Withdrawal amount must be greater than 0.")

        if amount > MAX_TRANSACTION:
            raise ValueError(
                f"Maximum withdrawal per transaction is ₹{MAX_TRANSACTION:,}."
            )

        if amount > account["balance"]:
            raise ValueError("Insufficient balance.")

        account["balance"] -= amount
        self._add_transaction(account, "Withdrawal", amount)
        self._save()

    @staticmethod
    def _add_transaction(account: dict, transaction_type: str, amount: int):
        account.setdefault("transactions", []).append(
            {
                "type": transaction_type,
                "amount": amount,
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        )

        # Keep only the most recent 50 transactions.
        account["transactions"] = account["transactions"][-50:]

    def update_account(
        self,
        account: dict,
        name: str,
        email: str,
        new_pin: str,
    ):
        if not name.strip():
            raise ValueError("Name cannot be empty.")

        if "@" not in email or "." not in email.split("@")[-1]:
            raise ValueError("Please enter a valid email address.")

        if not self._valid_pin(new_pin):
            raise ValueError("PIN must contain exactly 4 digits.")

        account["name"] = name.strip()
        account["email"] = email.strip().lower()

        # Keep the same salt/hash pattern as account creation.
        salt_hex, hash_hex = self._hash_pin(new_pin)
        account["pin_salt"] = salt_hex
        account["pin_hash"] = hash_hex
        account.pop("pin", None)

        self._save()

    def delete_account(self, account: dict):
        self.data.remove(account)
        self._save()


# ============================================================
# Streamlit helpers
# ============================================================

@st.cache_resource
def get_bank():
    return Bank()


def logout():
    st.session_state.pop("logged_in_account", None)


def get_logged_in_account():
    return st.session_state.get("logged_in_account")


def require_login():
    account = get_logged_in_account()

    if not account:
        st.warning("Please log in from the sidebar first.")
        st.stop()

    return account


# ============================================================
# Page configuration
# ============================================================

st.set_page_config(
    page_title="MyBank",
    page_icon="🏦",
    layout="wide",
)

st.title("🏦 MyBank")
st.caption("A Streamlit banking management project")


bank = get_bank()


# ============================================================
# Sidebar / Navigation
# ============================================================

logged_in = get_logged_in_account()

with st.sidebar:
    st.header("🏦 MyBank")

    if logged_in:
        st.success(f"Logged in as **{logged_in['name']}**")
        st.caption(f"Account: {logged_in['accountNo']}")
        st.caption(f"Balance: ₹{logged_in['balance']:,}")

        if st.button("🚪 Logout", use_container_width=True):
            logout()
            st.rerun()

        page = st.radio(
            "Choose an option",
            [
                "🏠 Dashboard",
                "💰 Deposit Money",
                "💸 Withdraw Money",
                "👤 My Details",
                "✏️ Update Details",
                "🗑️ Delete Account",
            ],
        )

    else:
        st.info("You are not logged in.")

        page = st.radio(
            "Choose an option",
            [
                "🏠 Dashboard",
                "🔐 Login",
                "🆕 Create Account",
            ],
        )


# ============================================================
# Login
# ============================================================

if page == "🔐 Login":
    st.subheader("🔐 Login to Your Account")
    st.write("Use the account number and 4-digit PIN you received when creating your account.")

    with st.form("login_form"):
        account_number = st.text_input(
            "Account Number",
            placeholder="Enter your 10-digit account number",
        )
        pin = st.text_input(
            "4-digit PIN",
            type="password",
            max_chars=4,
        )

        submitted = st.form_submit_button(
            "Login",
            use_container_width=True,
        )

    if submitted:
        account_number = account_number.strip()

        if not account_number:
            st.error("Please enter your account number.")
        elif not bank._valid_pin(pin):
            st.error("PIN must contain exactly 4 digits.")
        else:
            account = bank.authenticate(account_number, pin)

            if account:
                st.session_state.logged_in_account = account
                st.success("✅ Login successful!")
                st.rerun()
            else:
                st.error("❌ Invalid account number or PIN.")


# ============================================================
# Dashboard
# ============================================================

if page == "🏠 Dashboard":
    st.subheader("Welcome to MyBank")

    total_accounts = len(bank.data)
    total_balance = sum(account.get("balance", 0) for account in bank.data)
    total_transactions = sum(
        len(account.get("transactions", []))
        for account in bank.data
    )

    col1, col2, col3 = st.columns(3)

    col1.metric("Total Accounts", total_accounts)
    col2.metric("Total Bank Balance", f"₹{total_balance:,}")
    col3.metric("Transactions", total_transactions)

    st.divider()

    account = get_logged_in_account()

    if account:
        st.subheader("Your Account")

        c1, c2, c3 = st.columns(3)
        c1.metric("Name", account["name"])
        c2.metric("Account Number", account["accountNo"])
        c3.metric("Balance", f"₹{account['balance']:,}")

        transactions = account.get("transactions", [])

        if transactions:
            st.subheader("Recent Transactions")

            rows = [
                {
                    "Date & Time": tx["time"],
                    "Type": tx["type"],
                    "Amount": f"₹{tx['amount']:,}",
                }
                for tx in reversed(transactions[-10:])
            ]

            st.dataframe(rows, use_container_width=True, hide_index=True)
        else:
            st.info("No transactions yet.")
    else:
        st.info(
            "Create an account or log in using the sidebar to access "
            "account-specific features."
        )


# ============================================================
# Create Account
# ============================================================

elif page == "🆕 Create Account":
    st.subheader("Create a New Account")

    with st.form("create_account_form"):
        col1, col2 = st.columns(2)

        with col1:
            name = st.text_input("Full Name")
            age = st.number_input(
                "Age",
                min_value=1,
                max_value=120,
                value=18,
                step=1,
            )
            email = st.text_input("Email", placeholder="example@gmail.com")

        with col2:
            pin = st.text_input(
                "Create 4-digit PIN",
                type="password",
                max_chars=4,
            )
            confirm_pin = st.text_input(
                "Confirm PIN",
                type="password",
                max_chars=4,
            )

        submitted = st.form_submit_button(
            "Create Account",
            use_container_width=True,
        )

    if submitted:
        name = name.strip()
        email = email.strip().lower()

        if age < 18:
            st.error("You must be at least 18 years old.")

        elif not name:
            st.error("Please enter your name.")

        elif "@" not in email or "." not in email.split("@")[-1]:
            st.error("Please enter a valid email address.")

        elif not bank._valid_pin(pin):
            st.error("PIN must contain exactly 4 digits.")

        elif pin != confirm_pin:
            st.error("PINs do not match.")

        else:
            account = bank.create_account(name, int(age), email, pin)

            st.success("✅ Account created successfully!")

            st.info(
                f"Your account number is: **{account['accountNo']}**\n\n"
                "Save this number. You will need it to log in."
            )

            st.success("Go to **🔐 Login** from the sidebar and sign in with your account number and PIN.")


# ============================================================
# Deposit
# ============================================================

elif page == "💰 Deposit Money":
    st.subheader("Deposit Money")

    account = require_login()

    st.metric("Current Balance", f"₹{account['balance']:,}")

    with st.form("deposit_form"):
        amount = st.number_input(
            "Amount to deposit",
            min_value=1,
            max_value=MAX_TRANSACTION,
            value=100,
            step=100,
        )

        submitted = st.form_submit_button(
            "Deposit",
            use_container_width=True,
        )

    if submitted:
        try:
            bank.deposit(account, int(amount))
            st.success(f"₹{int(amount):,} deposited successfully.")
            st.metric("New Balance", f"₹{account['balance']:,}")
        except ValueError as err:
            st.error(str(err))


# ============================================================
# Withdraw
# ============================================================

elif page == "💸 Withdraw Money":
    st.subheader("Withdraw Money")

    account = require_login()

    st.metric("Available Balance", f"₹{account['balance']:,}")

    with st.form("withdraw_form"):
        amount = st.number_input(
            "Amount to withdraw",
            min_value=1,
            max_value=MAX_TRANSACTION,
            value=100,
            step=100,
        )

        submitted = st.form_submit_button(
            "Withdraw",
            use_container_width=True,
        )

    if submitted:
        try:
            bank.withdraw(account, int(amount))
            st.success(f"₹{int(amount):,} withdrawn successfully.")
            st.metric("New Balance", f"₹{account['balance']:,}")
        except ValueError as err:
            st.error(str(err))


# ============================================================
# My Details
# ============================================================

elif page == "👤 My Details":
    st.subheader("My Account Details")

    account = require_login()

    col1, col2 = st.columns(2)

    with col1:
        st.write(f"**Name:** {account['name']}")
        st.write(f"**Age:** {account['age']}")
        st.write(f"**Email:** {account['email']}")

    with col2:
        st.write(f"**Account Number:** {account['accountNo']}")
        st.write(f"**Balance:** ₹{account['balance']:,}")
        st.write(f"**Created:** {account.get('created_at', 'Not available')}")

    st.warning("Your PIN is never displayed.")


# ============================================================
# Update Details
# ============================================================

elif page == "✏️ Update Details":
    st.subheader("Update Account Details")

    account = require_login()

    with st.form("update_form"):
        name = st.text_input("Name", value=account["name"])
        email = st.text_input("Email", value=account["email"])
        new_pin = st.text_input(
            "New 4-digit PIN",
            type="password",
            max_chars=4,
            help="You must enter a new 4-digit PIN.",
        )
        confirm_new_pin = st.text_input(
            "Confirm new PIN",
            type="password",
            max_chars=4,
        )

        submitted = st.form_submit_button(
            "Update Details",
            use_container_width=True,
        )

    if submitted:
        if new_pin != confirm_new_pin:
            st.error("PINs do not match.")
        else:
            try:
                bank.update_account(account, name, email, new_pin)
                st.success("✅ Account details updated successfully.")
            except ValueError as err:
                st.error(str(err))


# ============================================================
# Delete Account
# ============================================================

elif page == "🗑️ Delete Account":
    st.subheader("Delete Account")

    account = require_login()

    st.error(
        "⚠️ Deleting your account permanently removes the account "
        "and its transaction history from data.json."
    )

    with st.form("delete_form"):
        confirmation = st.checkbox(
            "I understand that this action cannot be undone."
        )

        submitted = st.form_submit_button(
            "Delete My Account",
            use_container_width=True,
        )

    if submitted:
        if not confirmation:
            st.error("Please confirm the deletion first.")
        else:
            bank.delete_account(account)
            logout()
            st.success("Account deleted successfully.")
            st.rerun()


# ============================================================
# Footer
# ============================================================

st.divider()
st.caption(
    "Educational project only — this is not suitable for handling real "
    "banking or financial data."
)
