from flask import Flask, render_template, request, redirect, url_for
import mysql.connector

app = Flask(__name__)

# Update these variables with your actual MySQL credentials
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',          # Default XAMPP/MySQL user is usually 'root'
    'password': 'jkljkljkl',  # Enter your MySQL password here
    'database': 'gym_db'
}

def get_db_connection():
    """Helper function to create a new database connection."""
    return mysql.connector.connect(**DB_CONFIG)

def init_db():
    # 1. Connect without specifying a database to create it if it doesn't exist
    conn = mysql.connector.connect(
        host=DB_CONFIG['host'],
        user=DB_CONFIG['user'],
        password=DB_CONFIG['password']
    )
    c = conn.cursor()
    c.execute(f"CREATE DATABASE IF NOT EXISTS {DB_CONFIG['database']}")
    conn.close()

    # 2. Reconnect with the specific database selected
    conn = get_db_connection()
    c = conn.cursor()
    # Note: Added an explicit 'id' column since MySQL doesn't have a hidden 'rowid'
    c.execute('''
        CREATE TABLE IF NOT EXISTS members (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255),
            plan VARCHAR(255)
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/')
def home():
    search_query = request.args.get('search', '')
    conn = get_db_connection()
    c = conn.cursor()
    
    if search_query:
        # Changed '?' to '%s' for MySQL placeholders
        c.execute("SELECT id, name, plan FROM members WHERE name LIKE %s", ('%' + search_query + '%',))
    else:
        c.execute("SELECT id, name, plan FROM members")
        
    members = c.fetchall()
    conn.close()
    return render_template('index.html', members=members, search_query=search_query)

@app.route('/add', methods=['POST'])
def add_member():
    name = request.form['name']
    plan = request.form['plan']
    conn = get_db_connection()
    c = conn.cursor()
    # Changed '?' to '%s'
    c.execute("INSERT INTO members (name, plan) VALUES (%s, %s)", (name, plan))
    conn.commit()
    conn.close()
    return redirect(url_for('home'))

@app.route('/delete/<int:id>', methods=['POST'])
def delete_member(id):
    conn = get_db_connection()
    c = conn.cursor()
    # Changed 'rowid' to 'id' and '?' to '%s'
    c.execute("DELETE FROM members WHERE id=%s", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('home'))

if __name__ == '__main__':
    # Ensure your MySQL server (like XAMPP or MySQL Workbench) is running before starting the app
    init_db()
    app.run(debug=True)