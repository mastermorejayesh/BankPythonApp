import mysql.connector
import getpass

# Database Connection
conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="password",
    database="bank_db"
)
cursor = conn.cursor()

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

def register():
    name = input("Enter your name: ")
    email = input("Enter your email: ")
    phone = input("Enter your phone number: ")
    password = getpass.getpass("Enter a password: ")
    account_number = input("Enter a unique account number: ")
    
    try:
        cursor.execute("INSERT INTO customers (name, email, phone, password, account_number, balance) VALUES (%s, %s, %s, %s, %s, 0.00)", 
                       (name, email, phone, password, account_number))
        conn.commit()
        print("Account successfully created!")
    except mysql.connector.Error as err:
        print("Error:", err)

def login():
    account_number = input("Enter your account number: ")
    password = getpass.getpass("Enter your password: ")
    
    cursor.execute("SELECT * FROM customers WHERE account_number=%s AND password=%s", (account_number, password))
    user = cursor.fetchone()
    
    if user:
        print(f"Welcome {user[1]}!")
        banking_menu(account_number)
    else:
        print("Invalid credentials!")

def banking_menu(account_number):
    while True:
        print("\n1. Check Balance\n2. Deposit Money\n3. Withdraw Money\n4. Transfer Money\n5. Exit")
        choice = input("Choose an option: ")
        
        if choice == '1':
            check_balance(account_number)
        elif choice == '2':
            deposit(account_number)
        elif choice == '3':
            withdraw(account_number)
        elif choice == '4':
            transfer(account_number)
        elif choice == '5':
            break
        else:
            print("Invalid choice, try again!")

def check_balance(account_number):
    cursor.execute("SELECT balance FROM customers WHERE account_number=%s", (account_number,))
    balance = cursor.fetchone()[0]
    print(f"Your current balance: ₹{balance}")

def deposit(account_number):
    amount = float(input("Enter amount to deposit: "))
    cursor.execute("UPDATE customers SET balance = balance + %s WHERE account_number=%s", (amount, account_number))
    cursor.execute("INSERT INTO transactions (account_number, transaction_type, amount) VALUES (%s, 'deposit', %s)", (account_number, amount))
    conn.commit()
    print("Deposit successful!")

def withdraw(account_number):
    amount = float(input("Enter amount to withdraw: "))
    cursor.execute("SELECT balance FROM customers WHERE account_number=%s", (account_number,))
    balance = cursor.fetchone()[0]
    if balance >= amount:
        cursor.execute("UPDATE customers SET balance = balance - %s WHERE account_number=%s", (amount, account_number))
        cursor.execute("INSERT INTO transactions (account_number, transaction_type, amount) VALUES (%s, 'withdraw', %s)", (account_number, amount))
        conn.commit()
        print("Withdrawal successful!")
    else:
        print("Insufficient funds!")

def transfer(account_number):
    receiver = input("Enter receiver's account number: ")
    amount = float(input("Enter amount to transfer: "))
    cursor.execute("SELECT balance FROM customers WHERE account_number=%s", (account_number,))
    sender_balance = cursor.fetchone()[0]
    if sender_balance >= amount:
        cursor.execute("UPDATE customers SET balance = balance - %s WHERE account_number=%s", (amount, account_number))
        cursor.execute("UPDATE customers SET balance = balance + %s WHERE account_number=%s", (amount, receiver))
        cursor.execute("INSERT INTO transactions (account_number, transaction_type, amount, receiver_account) VALUES (%s, 'transfer', %s, %s)", (account_number, amount, receiver))
        conn.commit()
        print("Transfer successful!")
    else:
        print("Insufficient funds!")

if __name__ == "__main__":
    initialize_db()
    while True:
        print("\n1. Register\n2. Login\n3. Exit")
        user_choice = input("Choose an option: ")
        if user_choice == '1':
            register()
        elif user_choice == '2':
            login()
        elif user_choice == '3':
            break
        else:
            print("Invalid choice, try again!")
