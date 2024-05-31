from flask import Flask, redirect, url_for, render_template, request, session, flash
from datetime import timedelta
from flask_mysqldb import MySQL
from flask import jsonify
import hashlib 

app = Flask(__name__)
app.secret_key = "HolaCopa"
app.permanent_session_lifetime = timedelta(minutes= 30)
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'Jethru24'
app.config['MYSQL_DB'] = 'octacore'

mysql = MySQL(app)
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        # Hash the password using SHA-256
        password_hash = hashlib.sha256(password.encode()).hexdigest()

        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO users (name, email, password_hash) VALUES (%s, %s, %s)", (name, email, password_hash))
        mysql.connection.commit()
        cur.close()

        session["user"] = name
        session["email"] = email
        flash("Registration Successful!")
        return redirect(url_for("login"))

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        session.permanent = True
        email = request.form["email"]
        password = request.form["password"]

        cur = mysql.connection.cursor()
        cur.execute("SELECT name, password_hash FROM users WHERE email = %s", [email])
        user = cur.fetchone()
        cur.close()

        if user is None:
            flash("No account found with that email. Please register.")
            return redirect(url_for("register"))

        name, password_hash = user

        # Check if the password is correct
        if hashlib.sha256(password.encode()).hexdigest() != password_hash:
            flash("Incorrect password. Please try again.")
            return redirect(url_for("login"))

        # Check if the user is an administrator
        if email in [ "admin249@iitgn.ac.in", "pseudo@iitgn.ac.in"]:
            session["user"] = name
            session["email"] = email
            flash("Login Successful, Admin!")
            return redirect(url_for("use"))  # Redirect to admin page

        session["user"] = name
        session["email"] = email
        flash("Login Successful!")
        return redirect(url_for("user"))

    else:
        if "user" in session:
            flash("Already Logged In!")
            return redirect(url_for("user"))

        return render_template("login.html")


@app.route("/logout")
def logout():
    flash("You have been logged out!", "info")
    # Check if the email is in the session
    if "email" in session:
        session.pop("email", None)
    session.pop("user", None)
    return redirect(url_for("login"))



@app.route("/insert", methods = ["POST", "GET"])
def insert():
    # Check if the user is logged in
    if "user" not in session:
        flash("You are not logged in!")
        return redirect(url_for("login"))
    
    # Check if the user is an administrator
    if session["user"] not in ["admin", "PseudoAdmin"] or session["email"] not in ["admin249@iitgn.ac.in", "pseudo@iitgn.ac.in"]:
        flash("You are not authorized to perform this action!")
        return redirect(url_for("user"))
    
    cur = mysql.connection.cursor()

    # Fetch table names
    cur.execute("SHOW TABLES")
    tables = [table[0] for table in cur.fetchall() if table[0] != 'users']

    if request.method == 'POST':
        table_name = request.form['table_name']
        attribute_values = request.form.getlist('attribute_values[]')

        # Fetch attribute names for the selected table
        cur.execute(f"SHOW COLUMNS FROM {table_name}")
        attributes = [column[0] for column in cur.fetchall()]

        values = [f"'{value}'" for value in attribute_values if value]
        attributes = [attributes[i] for i, value in enumerate(attribute_values) if value]

        if values:
            values_str = ', '.join(values)
            attributes_str = ', '.join(attributes)
            query = f"INSERT INTO {table_name} ({attributes_str}) VALUES ({values_str})"
            cur.execute(query)
            mysql.connection.commit()
            cur.close()

            return jsonify({"success": True})
        else:
            cur.close()
            return jsonify({"success": False, "message": "No attributes provided for insertion"})

    cur.close()
    return render_template('insert.html', tables=tables)


@app.route('/delete', methods=['GET','POST'])
def delete():
    if "user" not in session:
        flash("You are not logged in!")
        return redirect(url_for("login"))
    
    # Check if the user is an administrator
    if session["user"] not in ["admin", "PseudoAdmin"] or session["email"] not in ["admin249@iitgn.ac.in", "pseudo@iitgn.ac.in"]:
        flash("You are not authorized to perform this action!")
        return redirect(url_for("user"))
    
    cur = mysql.connection.cursor()

    # Fetch table names
    cur.execute("SHOW TABLES")
    tables = [table[0] for table in cur.fetchall()  if table[0] != 'users']

    if request.method == 'POST':
        table_name = request.form['table_name']
        attribute_names = request.form.getlist('attribute_names[]')
        attribute_values = request.form.getlist('attribute_values[]')

        conditions = [f"{name} = '{value}'" for name, value in zip(attribute_names, attribute_values) if value]
        if conditions:
            condition_str = ' AND '.join(conditions)
            cur.execute(f"LOCK TABLES {table_name} WRITE")

            query = f"DELETE FROM {table_name} WHERE {condition_str}"
            cur.execute(query)
            mysql.connection.commit()

            cur.execute("UNLOCK TABLES")
            cur.close()

            return jsonify({"success": True})
        else:
            cur.close()
            return jsonify({"success": False, "message": "No attributes provided for deletion."})
    cur.close()
    return render_template('delete.html', tables=tables)


@app.route('/update', methods=['GET','POST'])
def update():
    # Check if the user is logged in
    if "user" not in session:
        flash("You are not logged in!")
        return redirect(url_for("login"))
    
    # Check if the user is an administrator
    if session["user"] not in ["admin", "PseudoAdmin"] or session["email"] not in ["admin249@iitgn.ac.in", "pseudo@iitgn.ac.in"]:
        flash("You are not authorized to perform this action!")
        return redirect(url_for("user"))
    
    cur = mysql.connection.cursor()

    # Fetch table names
    cur.execute("SHOW TABLES")
    tables = [table[0] for table in cur.fetchall()  if table[0] != 'users']

    if request.method == 'POST':
        table_name = request.form['table_name']
        attribute_names = request.form.getlist('attribute_names[]')
        attribute_values = request.form.getlist('attribute_values[]')
        update_attribute = request.form['update_attribute']
        update_value = request.form['update_value']

        conditions = [f"{name} = '{value}'" for name, value in zip(attribute_names, attribute_values) if value]
        if conditions:
            condition_str = ' AND '.join(conditions)

            cur.execute(f"LOCK TABLES {table_name} WRITE")
            query = f"UPDATE {table_name} SET {update_attribute} = '{update_value}' WHERE {condition_str}"
            cur.execute(query)
            mysql.connection.commit()
            cur.execute(f"UNLOCK TABLES")

            cur.close()
            return jsonify({"success": True})
        
        else:
            cur.execute(f"UNLOCK TABLES")
            cur.close()
            return jsonify({"success": False, "message": "No attributes provided to update."})
    cur.close()
    return render_template('update.html', tables=tables)


@app.route('/rename', methods=['GET', 'POST'])
def rename():
    # Check if the user is logged in
    if "user" not in session:
        flash("You are not logged in!")
        return redirect(url_for("login"))
    
    # Check if the user is an administrator
    if session["user"] not in ["admin", "PseudoAdmin"] or session["email"] not in ["admin249@iitgn.ac.in", "pseudo@iitgn.ac.in"]:
        flash("You are not authorized to perform this action!")
        return redirect(url_for("user"))
    
    cur = mysql.connection.cursor()
    cur.execute("SHOW TABLES")
    tables = [table[0] for table in cur.fetchall()  if table[0] != 'users']

    if request.method == 'POST':
        old_table_name = request.form['old_table_name']
        new_table_name = request.form['new_table_name']
        
        try:
            cur.execute(f"LOCK TABLES {old_table_name} WRITE")
            query = f"RENAME TABLE {old_table_name} TO {new_table_name}"
            cur.execute(query)
            mysql.connection.commit()
            cur.execute(f"UNLOCK TABLES")
            cur.close()
            return jsonify({"success": True})
        
        except Exception as e:
            cur.execute(f"UNLOCK TABLES")
            cur.close()
            return jsonify({"success": False, "message": str(e)})

    cur.close()
    return render_template('rename.html', tables=tables)


        
@app.route('/user', methods=['GET', 'POST'])
def user():
    if "user" in session:
        user = session["user"]
        if request.method == 'POST':
            cur = mysql.connection.cursor()
            query = '''SELECT * FROM ((SELECT CONCAT_WS(' ', ts.FirstName, ts.MiddleName, ts.LastName) AS Name, jd.Designation AS Designation, ts.Email AS Email,jd.Discipline_name AS Discipline_Section, p.Work AS Work,CONCAT_WS('/', IFNULL(p.Home, ''), IFNULL(p.Emergency, '')) AS Home_Emerg, CONCAT_WS('/', jd.Building, jd.Room_number) AS Office FROM Teaching_staff ts JOIN Specialization s ON ts.Faculty_ID = s.Faculty_ID JOIN Job_desc jd ON s.Discipline_name = jd.Discipline_name JOIN Contact c ON ts.Faculty_ID = c.Faculty_ID JOIN Phone p ON c.Work = p.Work AND s.Designation = jd.Designation AND s.Room_number = jd.Room_number AND s.Building = jd.Building) UNION All (SELECT CONCAT_WS(' ', nts.F_name, nts.M_name, nts.L_name) AS Name, jd.Designation AS Designation, nts.EmailID AS Email, jd.Discipline_name AS Discipline_Section, p.Work AS Work, CONCAT_WS('/', IFNULL(p.Home, ''), IFNULL(p.Emergency, '')) AS Home_Emerg, CONCAT_WS('/', jd.Building, jd.Room_number) AS Office  FROM NTeaching_staff nts  JOIN Work_info wi ON nts.Staff_ID = wi.Staff_ID JOIN Job_desc jd ON wi.Discipline_name = jd.Discipline_name JOIN Contact_enquiry ce ON nts.Staff_ID = ce.Staff_ID JOIN Phone p ON ce.Work = p.Work AND wi.Designation = jd.Designation AND wi.Room_number = jd.Room_number AND wi.Building = jd.Building) UNION All (SELECT CONCAT_WS(' ', st.First_name, st.Middle_name, st.Last_name) AS Name, st.Program AS Designation,st.Email_id AS Email,st.Discipline AS Discipline_Section,p.Work AS Work,CONCAT_WS('/', IFNULL(p.Home, ''), IFNULL(p.Emergency, '')) AS Home_Emerg, CONCAT_WS('/',' ') AS Office  FROM Students st  JOIN Contact_number cn ON st.Roll_number = cn.Roll_number  JOIN Phone p ON cn.Work = p.Work) UNION All (SELECT CONCAT_WS(' ', f.Facility_name) AS Name,' ' AS Designation, f.Email_addr AS Email,' ' AS Discipline_Section, p.Work AS Work, CONCAT_WS('/', IFNULL(p.Home, ''), IFNULL(p.Emergency, '')) AS Home_Emerg, CONCAT_WS('/', f.BuildingName, f.RoomNumber) AS Office  FROM Contact_info ci  JOIN Facility f ON ci.Facility_name = f.Facility_name   JOIN Phone p ON ci.Work = p.Work) UNION All (SELECT b.Block_name AS Name, ' ' AS Designation,' ' AS Email,' ' AS Discipline_Section,p.Work AS Work, CONCAT_WS('/', IFNULL(p.Home, ''), IFNULL(p.Emergency, '')) AS Home_Emerg, ' '  AS Office  FROM To_Contact tc  JOIN Block b ON tc.Block_name = b.Block_name  JOIN Phone p ON tc.Work = p.Work)) AS derived_table'''
            data = []
            # Search by Name/Email
            if 'search_term' in request.form:
                search_term = request.form['search_term']
                cur.execute(query + " WHERE Name LIKE %s OR Email LIKE %s ORDER BY Name", (f"%{search_term}%", f"%{search_term}%"))
                data.extend(cur.fetchall())

            # Search by Discipline/Section with Dropdown
            elif 'discipline_section' in request.form:
                discipline_section = request.form['discipline_section']
                cur.execute(query + " WHERE Discipline_Section LIKE %s ORDER BY Name", (f"%{discipline_section}%",))
                data.extend(cur.fetchall())

            cur.close()
            return render_template('index1.html', data=data)

        return render_template('index1.html')
    
    else:
        flash("You are not logged In!")
        return redirect(url_for("login"))

@app.route('/use')
def use():
    # Check if the user is logged in
    if "user" not in session :
        flash("You are not logged in!")
        return redirect(url_for("login"))
    
    # Check if the user is an administrator
    if session["user"] not in ["admin", "PseudoAdmin"] or session["email"] not in ["admin249@iitgn.ac.in", "pseudo@iitgn.ac.in"]:
        flash("You are not authorized to perform this action!")
        return redirect(url_for("user"))
    
    cur = mysql.connection.cursor()
    cur.execute("SHOW TABLES")
    tables = [table[0] for table in cur.fetchall()  if table[0] != 'users']
    cur.close()
    return render_template('use.html', tables=tables)

@app.route('/usage/<table_name>', methods=['GET', 'POST'])
def usage(table_name):
    # Check if the user is logged in
    if "user" not in session:
        flash("You are not logged in!")
        return redirect(url_for("login"))
    
    # Check if the user is an administrator
    if session["user"] not in ["admin", "PseudoAdmin"] or session["email"] not in ["admin249@iitgn.ac.in", "pseudo@iitgn.ac.in"]:
        flash("You are not authorized to perform this action!")
        return redirect(url_for("user"))
    
    cur = mysql.connection.cursor()
    cur.execute(f"SHOW COLUMNS FROM {table_name}")
    attributes = [column[0] for column in cur.fetchall()]

    if request.method == 'POST':
        query = f"SELECT * FROM {table_name} WHERE "
        for attribute in attributes:
            value = request.form.get(attribute)
            if value:
                query += f"{attribute}='{value}' AND "
        query = query.rstrip(' AND ')
        cur.execute(query)
        records = cur.fetchall()
    else:
        cur.execute(f"SELECT * FROM {table_name}")
        records = cur.fetchall()

    cur.close()
    return render_template('usage.html', table_name=table_name, attributes=attributes, records=records)

@app.route('/relations', methods=['GET','POST'])
def relations():
    # Check if the user is logged in
    if "user" not in session:
        flash("You are not logged in!")
        return redirect(url_for("login"))
    
    # Check if the user is an administrator
    if session["user"] not in ["admin", "PseudoAdmin"] or session["email"] not in ["admin249@iitgn.ac.in", "pseudo@iitgn.ac.in"]:
        flash("You are not authorized to perform this action!")
        return redirect(url_for("user"))
    
    return render_template('relations.html')


@app.route('/get_attributes', methods=['GET'])
def get_attributes():
    table_name = request.args.get('table_name')

    cur = mysql.connection.cursor()

    # Fetch attribute names for the selected table
    cur.execute(f"SHOW COLUMNS FROM {table_name}")
    attributes = [column[0] for column in cur.fetchall()]

    cur.close()

    return jsonify({'attributes': attributes})

if __name__ == "__main__":
    app.run(debug = True)
