from flask import Flask, render_template, request, redirect, url_for, flash
import mysql.connector
import getpass
from werkzeug.security import generate_password_hash, check_password_hash
import matplotlib.pyplot as plt
import io
import base64
from flask import session

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Secret key for sessions

# Database Connection (Updated for Docker)
conn = mysql.connector.connect(
    host="localhost",  # The service name defined in docker-compose.yml for MySQL
    user="root",
    password="password",  # The root password defined in docker-compose.yml
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

# Home page route
@app.route('/')
def home():
    return render_template('index.html')

# Register route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        password = request.form['password']
        account_number = request.form['account_number']

        print(f"Received: {name}, {email}, {phone}, {account_number}")  # Debugging

        # Hash the password
        hashed_password = generate_password_hash(password)

        try:
            cursor.execute("INSERT INTO customers (name, email, phone, password, account_number, balance) VALUES (%s, %s, %s, %s, %s, 0.00)",
                           (name, email, phone, hashed_password, account_number))
            conn.commit()
            flash("Account successfully created!", "success")
            return redirect(url_for('home'))
        except mysql.connector.Error as err:
            flash(f"Error: {err}", "error")
            return render_template('register.html')

    return render_template('register.html')

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        account_number = request.form['account_number']
        password = request.form['password']

        cursor.execute("SELECT * FROM customers WHERE account_number=%s", (account_number,))
        user = cursor.fetchone()

        if user and check_password_hash(user[4], password):
            return redirect(url_for('banking_menu', account_number=account_number))
        else:
            flash("Invalid credentials!", "error")
            return render_template('login.html')

    return render_template('login.html')

# Banking Menu route
@app.route('/banking_menu/<account_number>', methods=['GET', 'POST'])
def banking_menu(account_number):
    cursor.execute("SELECT name, email, phone, balance FROM customers WHERE account_number=%s", (account_number,))
    user_data = cursor.fetchone()

    cursor.execute("SELECT transaction_type, amount, receiver_account, transaction_date FROM transactions WHERE account_number=%s ORDER BY transaction_date DESC LIMIT 5", (account_number,))
    transactions = cursor.fetchall()

    if request.method == 'POST':
        action = request.form['action']
        amount = float(request.form['amount'])

        if action == 'deposit':
            cursor.execute("UPDATE customers SET balance = balance + %s WHERE account_number=%s", (amount, account_number))
            cursor.execute("INSERT INTO transactions (account_number, transaction_type, amount) VALUES (%s, 'deposit', %s)", (account_number, amount))
            flash("Deposit successful!", "success")

        elif action == 'withdraw':
            if user_data[3] >= amount:
                cursor.execute("UPDATE customers SET balance = balance - %s WHERE account_number=%s", (amount, account_number))
                cursor.execute("INSERT INTO transactions (account_number, transaction_type, amount) VALUES (%s, 'withdraw', %s)", (account_number, amount))
                flash("Withdrawal successful!", "success")
            else:
                flash("Insufficient funds!", "error")

        elif action == 'transfer':
            receiver_account = request.form['receiver_account']
            if user_data[3] >= amount:
                cursor.execute("UPDATE customers SET balance = balance - %s WHERE account_number=%s", (amount, account_number))
                cursor.execute("UPDATE customers SET balance = balance + %s WHERE account_number=%s", (amount, receiver_account))
                cursor.execute("INSERT INTO transactions (account_number, transaction_type, amount, receiver_account) VALUES (%s, 'transfer', %s, %s)", (account_number, amount, receiver_account))
                flash("Transfer successful!", "success")
            else:
                flash("Insufficient funds!", "error")

        conn.commit()
        return redirect(url_for('banking_menu', account_number=account_number))

    return render_template('banking_menu.html', account_number=account_number, user_data=user_data, transactions=transactions)

# Edit Account Details
@app.route('/edit_account/<account_number>', methods=['GET', 'POST'])
def edit_account(account_number):
    cursor.execute("SELECT name, email, phone FROM customers WHERE account_number=%s", (account_number,))
    user_data = cursor.fetchone()

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']

        cursor.execute("UPDATE customers SET name=%s, email=%s, phone=%s WHERE account_number=%s", (name, email, phone, account_number))
        conn.commit()
        flash("Account details updated successfully!", "success")
        return redirect(url_for('banking_menu', account_number=account_number))

    return render_template('edit_account.html', account_number=account_number, user_data=user_data)
# Admin page route (accessible after successful login)

# Admin Login route
@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    # Define the admin password (for simplicity, hardcoded here)
    admin_password = 'admin123'  # Change this to your desired password

    if request.method == 'POST':
        password = request.form['password']

        if password == admin_password:
            return redirect(url_for('admin_page'))  # Redirect to admin page if correct password
        else:
            return render_template('admin_login.html', message="Incorrect password. Please try again.")

    return render_template('admin_login.html')

@app.route('/admin', methods=['GET'])
def admin_page():
    # Only allow access if the user has logged in as admin
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))  # Redirect to login page if not logged in

    # Get all users and their balances
    cursor.execute("SELECT id, name, account_number, balance FROM customers")
    users = cursor.fetchall()

    # Get total money in the bank
    cursor.execute("SELECT SUM(balance) FROM customers")
    total_money = cursor.fetchone()[0]

    # Get transaction statistics (deposit, withdraw, transfer)
    cursor.execute("""
        SELECT
            transaction_type,
            SUM(amount)
        FROM
            transactions
        GROUP BY transaction_type
    """)
    transaction_stats = cursor.fetchall()

    # Prepare data for graph (Deposits, Withdrawals, Transfers)
    transaction_types = ['Deposit', 'Withdraw', 'Transfer']
    transaction_values = [0, 0, 0]
    for stat in transaction_stats:
        if stat[0] == 'deposit':
            transaction_values[0] = stat[1]
        elif stat[0] == 'withdraw':
            transaction_values[1] = stat[1]
        elif stat[0] == 'transfer':
            transaction_values[2] = stat[1]

    # Generate graph image
    fig, ax = plt.subplots()
    ax.bar(transaction_types, transaction_values, color=['green', 'red', 'blue'])
    ax.set_title('Total Transactions in Bank')
    ax.set_ylabel('Amount')

    # Save plot to a BytesIO object
    img_io = io.BytesIO()
    fig.savefig(img_io, format='png')
    img_io.seek(0)
    img_base64 = base64.b64encode(img_io.getvalue()).decode('utf-8')

    return render_template('admin_page.html', users=users, total_money=total_money, img_base64=img_base64)

@app.route('/admin_logout')
def admin_logout():
    session.pop('admin_logged_in', None)  # Remove admin session
    return redirect(url_for('admin_login'))





if __name__ == '__main__':
    initialize_db()
    app.run(debug=True)
