import mysql.connector
import getpass
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Database credentials from .env file
DB_HOST = os.getenv('DB_HOST')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_NAME = os.getenv('DB_NAME')

# Database Connection
conn = mysql.connector.connect(
    host=DB_HOST,
    user=DB_USER,
    password=DB_PASSWORD,
    database=DB_NAME
)
cursor = conn.cursor()

# Hardcoded Admin credentials (for simplicity)
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD_HASH = generate_password_hash("password", method='pbkdf2:sha256')  # Correct hashing method
# Function to create necessary tables
def initialize_db():
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100),
            email VARCHAR(100) UNIQUE,
            phone VARCHAR(15),
            password VARCHAR(255),
            account_number VARCHAR(20) UNIQUE,
            balance DECIMAL(10,2) DEFAULT 0.00,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            account_number VARCHAR(20),
            transaction_type ENUM('deposit', 'withdraw', 'transfer'),
            amount DECIMAL(10,2),
            receiver_account VARCHAR(20) NULL,
            transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (account_number) REFERENCES customers(account_number)
        )
    """)
    conn.commit()

# Function to authenticate admin login
def admin_login():
    username = input("Enter admin username: ")
    password = getpass.getpass("Enter admin password: ")

    if username == ADMIN_USERNAME and check_password_hash(ADMIN_PASSWORD_HASH, password):
        print("Admin login successful!")
        admin_menu()
    else:
        print("Invalid admin credentials!")

# Admin CLI Menu
def admin_menu():
    while True:
        print("\nAdmin Menu:")
        print("1. View All Users")
        print("2. Update User Details")
        print("3. Delete User")
        print("4. View Transactions")
        print("5. Exit")
        
        choice = input("Choose an option: ")

        if choice == '1':
            view_all_users()
        elif choice == '2':
            update_user_details()
        elif choice == '3':
            delete_user()
        elif choice == '4':
            view_transactions()
        elif choice == '5':
            break
        else:
            print("Invalid choice, please try again.")

# View all registered users
def view_all_users():
    cursor.execute("SELECT id, name, email, account_number, balance FROM customers")
    users = cursor.fetchall()

    if users:
        print("\nAll Users:")
        for user in users:
            print(f"ID: {user[0]} | Name: {user[1]} | Email: {user[2]} | Account Number: {user[3]} | Balance: ₹{user[4]}")
    else:
        print("No users found.")

# Update user details
def update_user_details():
    account_number = input("Enter the account number of the user to update: ")

    cursor.execute("SELECT * FROM customers WHERE account_number=%s", (account_number,))
    user = cursor.fetchone()

    if user:
        print("User found. Enter new details:")
        new_name = input(f"Enter new name (current: {user[1]}): ")
        new_email = input(f"Enter new email (current: {user[2]}): ")
        new_phone = input(f"Enter new phone (current: {user[3]}): ")

        cursor.execute("""
            UPDATE customers SET name=%s, email=%s, phone=%s WHERE account_number=%s
        """, (new_name, new_email, new_phone, account_number))
        conn.commit()

        print(f"User {user[1]} details updated successfully!")
    else:
        print("User not found.")

# Delete a user
def delete_user():
    account_number = input("Enter the account number of the user to delete: ")
    
    # Define the default account number (you can set this to whatever account you want the funds to be transferred to)
    default_account_number = "999"  # Replace with your actual default account number

    try:
        # Retrieve the user's balance before deleting
        cursor.execute("SELECT balance FROM customers WHERE account_number=%s", (account_number,))
        user_balance = cursor.fetchone()
        
        if user_balance:
            # Transfer the balance to the default account before deletion
            cursor.execute("""
                UPDATE customers 
                SET balance = balance + %s 
                WHERE account_number = %s
            """, (user_balance[0], default_account_number))

            # Insert the transfer transaction into the transactions table
            cursor.execute("""
                INSERT INTO transactions (account_number, transaction_type, amount, receiver_account)
                VALUES (%s, 'transfer', %s, %s)
            """, (default_account_number, user_balance[0], account_number))
            
            # Now, delete the user’s transactions
            cursor.execute("DELETE FROM transactions WHERE account_number=%s", (account_number,))
            
            # Finally, delete the customer record
            cursor.execute("DELETE FROM customers WHERE account_number=%s", (account_number,))
            conn.commit()
            print(f"User with account number {account_number} has been deleted and their balance has been transferred to the default account.")
        else:
            print("No user found with that account number.")
    except mysql.connector.Error as err:
        print("Error:", err)
        conn.rollback()


# View all transactions
def view_transactions():
    cursor.execute("SELECT * FROM transactions")
    transactions = cursor.fetchall()

    if transactions:
        print("\nAll Transactions:")
        for transaction in transactions:
            print(f"ID: {transaction[0]} | Account: {transaction[1]} | Type: {transaction[2]} | Amount: ₹{transaction[3]} | Receiver: {transaction[4]} | Date: {transaction[5]}")
    else:
        print("No transactions found.")

# Main function
def main():
    initialize_db()

    while True:
        print("\n1. Admin Login\n2. Exit")
        user_choice = input("Choose an option: ")

        if user_choice == '1':
            admin_login()
        elif user_choice == '2':
            break
        else:
            print("Invalid choice, try again.")

if __name__ == "__main__":
    main()
