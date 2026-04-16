from flask import Flask, render_template, request, redirect, url_for
import mysql.connector

app = Flask(__name__)
app.secret_key = "super_secret_key"

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'jkljkljkl', # Update this if your MySQL has a password
    'database': 'gym_db_v4'
}

def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)

def init_db():
    # Connect to MySQL to create the database if it doesn't exist
    conn = mysql.connector.connect(host=DB_CONFIG['host'], user=DB_CONFIG['user'], password=DB_CONFIG['password'])
    c = conn.cursor()
    c.execute(f"CREATE DATABASE IF NOT EXISTS {DB_CONFIG['database']}")
    conn.close()

    # Reconnect to the specific database to build the tables
    conn = get_db_connection()
    c = conn.cursor()
    
    # Create the Plans table
    c.execute('''
        CREATE TABLE IF NOT EXISTS plans (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(50) UNIQUE NOT NULL,
            price DECIMAL(10, 2) NOT NULL,
            duration_days INT NOT NULL
        )
    ''')
    
    # Create the Members table (with the Soft Delete 'status' column)
    c.execute('''
        CREATE TABLE IF NOT EXISTS members (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            plan_id INT,
            join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status VARCHAR(20) DEFAULT 'Active', 
            FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE SET NULL
        )
    ''')
    
    # Insert default plans if the table is empty
    c.execute("SELECT COUNT(*) FROM plans")
    if c.fetchone()[0] == 0:
        c.execute('''
            INSERT INTO plans (name, price, duration_days) 
            VALUES ('Basic', 20.00, 30), ('Premium', 50.00, 90), ('VIP', 100.00, 365)
        ''')
    
    conn.commit()
    conn.close()

@app.route('/')
def home():
    conn = get_db_connection()
    c = conn.cursor(dictionary=True)
    
    # 1. Dashboard Stats (Only count Active members)
    c.execute('''
        SELECT p.name AS plan_name, COUNT(m.id) AS member_count 
        FROM plans p 
        LEFT JOIN members m ON p.id = m.plan_id AND m.status = 'Active'
        GROUP BY p.name
    ''')
    stats = c.fetchall()

    # 2. Roster Data (Only fetch Active members, calculate expiry dates)
    base_query = '''
        SELECT m.id, m.name, p.name AS plan_name, m.join_date, m.status,
               DATE_ADD(m.join_date, INTERVAL p.duration_days DAY) AS expiry_date,
               DATEDIFF(DATE_ADD(m.join_date, INTERVAL p.duration_days DAY), CURRENT_DATE) AS days_left
        FROM members m 
        LEFT JOIN plans p ON m.plan_id = p.id
        WHERE m.status = 'Active' 
    '''

    search_query = request.args.get('search', '')
    if search_query:
        c.execute(base_query + " AND m.name LIKE %s ORDER BY m.id DESC", ('%' + search_query + '%',))
    else:
        c.execute(base_query + " ORDER BY m.id DESC")
        
    members = c.fetchall()
    
    # 3. Get plans for the dropdown menu
    c.execute("SELECT * FROM plans")
    plans = c.fetchall()
    
    conn.close()
    return render_template('index.html', members=members, plans=plans, stats=stats, search_query=search_query)

@app.route('/add', methods=['POST'])
def add_member():
    name = request.form['name']
    plan_id = request.form['plan_id']
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO members (name, plan_id) VALUES (%s, %s)", (name, plan_id))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print("Database Error:", e)
    finally:
        conn.close()
    return redirect(url_for('home'))

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_member(id):
    conn = get_db_connection()
    c = conn.cursor(dictionary=True)
    
    if request.method == 'POST':
        new_name = request.form['name']
        new_plan_id = request.form['plan_id']
        new_status = request.form['status']
        c.execute("UPDATE members SET name=%s, plan_id=%s, status=%s WHERE id=%s", (new_name, new_plan_id, new_status, id))
        conn.commit()
        conn.close()
        return redirect(url_for('home'))
    
    c.execute("SELECT * FROM members WHERE id=%s", (id,))
    member = c.fetchone()
    c.execute("SELECT * FROM plans")
    plans = c.fetchall()
    conn.close()
    return render_template('edit.html', member=member, plans=plans)

@app.route('/cancel/<int:id>', methods=['POST'])
def cancel_member(id):
    # Soft Delete: Update status to 'Cancelled'
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("UPDATE members SET status='Cancelled' WHERE id=%s", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('home'))

# ---------------- NEW ARCHIVE FEATURES ----------------

@app.route('/archives')
def archives():
    conn = get_db_connection()
    c = conn.cursor(dictionary=True)
    
    # Fetch only 'Cancelled' members
    c.execute('''
        SELECT m.id, m.name, p.name AS plan_name, m.join_date, m.status
        FROM members m 
        LEFT JOIN plans p ON m.plan_id = p.id
        WHERE m.status = 'Cancelled' 
        ORDER BY m.id DESC
    ''')
    archived_members = c.fetchall()
    conn.close()
    
    return render_template('archives.html', members=archived_members)

@app.route('/reactivate/<int:id>', methods=['POST'])
def reactivate_member(id):
    conn = get_db_connection()
    c = conn.cursor()
    
    # Change status back to 'Active'
    c.execute("UPDATE members SET status='Active' WHERE id=%s", (id,))
    conn.commit()
    conn.close()
    
    return redirect(url_for('home'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
