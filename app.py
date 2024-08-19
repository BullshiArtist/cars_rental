import base64

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import mysql.connector
from mysql.connector import errorcode
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import timedelta

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.permanent_session_lifetime = timedelta(minutes=30)  # Set session timeout

# Configure your database connection
db_config = {
    'user': '',
    'password': '',
    'host': 'localhost',
    'database': 'car_rental'
}


def get_db_connection():
    try:
        conn = mysql.connector.connect(**db_config)
        return conn
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("Something is wrong with your user name or password")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            print("Database does not exist")
        else:
            print(err)
        return None


@app.route('/')
def homepage():
    return render_template('index.html')


@app.route('/sign_up', methods=['GET', 'POST'])
def sign_up():
    if request.method == 'POST':
        username = request.form.get('username')
        real_name = request.form.get('real_name')
        date_of_birth = request.form.get('date_of_birth')
        email = request.form.get('email')
        password = request.form.get('password')

        # Validate form data
        if not (username and real_name and date_of_birth and email and password):
            flash('Please fill out all fields', 'error')
            return redirect(url_for('sign_up'))

        # Hash the password
        password_hash = generate_password_hash(password)

        # Insert user into the database
        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO users (username, real_name, date_of_birth, email, password_hash, user_type) "
                    "VALUES (%s, %s, %s, %s, %s, %s)",
                    (username, real_name, date_of_birth, email, password_hash, 'user')
                )
                conn.commit()
                flash('Account created successfully!', 'success')
                return redirect(url_for('log_in'))
            except mysql.connector.Error as err:
                print(err)
                flash('Error creating account. Please try again.', 'error')
            finally:
                cursor.close()
                conn.close()

    return render_template('sign_up.html')


@app.route('/log_in', methods=['GET', 'POST'])
def log_in():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Validate form data
        if not (username and password):
            flash('Please fill out all fields', 'error')
            return redirect(url_for('log_in'))

        # Authenticate user
        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
                user = cursor.fetchone()
                if user and check_password_hash(user['password_hash'], password):
                    # Start user session
                    session.permanent = True
                    session['user_id'] = user['id']
                    session['username'] = user['username']
                    session['user_type'] = user['user_type']

                    # Redirect based on user type
                    if user['user_type'] == 'user':
                        return redirect(url_for('index'))
                else:
                    flash('Invalid username or password', 'error')
            except mysql.connector.Error as err:
                flash('Error logging in. Please try again.', 'error')
            finally:
                cursor.close()
                conn.close()

    return render_template('log_in.html')


@app.route('/index')
def index():
    if 'username' in session:
        # return f"Welcome, {session['username']}! You are logged in as a user."
        return render_template('index_user.html')
    else:
        return redirect(url_for('log_in'))


@app.route('/index_admin')
def index_admin():
    if 'username' in session:
        return f"Welcome, {session['username']}! You are logged in as an admin."
    else:
        return redirect(url_for('log_in'))


@app.route('/logout')
def logout():
    match session['user_type']:
        case 'user':
            session.clear()
            return redirect(url_for('homepage'))
        case 'admin':
            session.clear()
            return redirect(url_for('admin_login'))


@app.route('/home')
def home():
    if 'username' in session:
        return render_template('index_user.html')
    else:
        return redirect(url_for('log_in'))


# explore the cars
@app.route('/explore_cars')
def explore_cars():
    if 'username' in session:
        return render_template('explore_car.html')
    else:
        return redirect(url_for('log_in'))


@app.route('/get_cars')
def get_cars():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch all cars including the 'picture' field
    cursor.execute(
        "SELECT id, brand, model, year, color, capacity, type, transmission, consumption, price, power, picture FROM cars")
    cars = cursor.fetchall()

    # Convert the picture (binary data) to base64 string for each car
    for car in cars:
        if car['picture']:
            car['picture'] = base64.b64encode(car['picture']).decode('utf-8')
        else:
            car['picture'] = None  # Handle cars with no picture

    cursor.close()
    conn.close()

    return jsonify(cars)


@app.route('/rent_car/<int:car_id>')
def rent_car(car_id):
    if 'username' in session:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM cars WHERE id = %s", (car_id,))
        car = cursor.fetchone()

        if car:
            if car['picture']:
                car['picture'] = f"data:image/jpeg;base64,{base64.b64encode(car['picture']).decode('utf-8')}"
            else:
                car['picture'] = None

        cursor.close()
        conn.close()

        return render_template('cart.html', car=car)

    else:
        return redirect(url_for('log_in'))


@app.route('/cars/<int:car_id>')
def cars(car_id):
    if 'username' in session:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM cars WHERE id = %s", (car_id,))
        car = cursor.fetchone()

        if car and car['picture']:
            car['picture'] = base64.b64encode(car['picture']).decode('utf-8')

        cursor.close()
        conn.close()

        if car:
            return render_template('car_details.html', car=car)
    else:
        return redirect(url_for('log_in'))


@app.route('/go_index')
def go_index():
    if 'username' in session:
        return redirect(url_for('index'))
    else:
        return redirect(url_for('homepage'))


@app.route('/cancel_reservation/<int:id>', methods=['POST'])
def cancel_reservation(id):
    connection = get_db_connection()
    cursor = connection.cursor()

    # Update the reservation status to 'cancelled'
    cursor.execute("UPDATE reservation SET status = 'cancelled' WHERE id = %s", (id,))
    connection.commit()

    cursor.close()
    connection.close()

    return jsonify(success=True)


@app.route('/reservation')
def reservation():
    user_id = session.get('user_id')

    if not user_id:
        return redirect('/log_in')
    else:
        return render_template('reservation.html')


@app.route('/get_reservations')
def get_reservations():
    user_id = session.get('user_id')

    if not user_id:
        return jsonify([])  # Return empty if not logged in

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # Fetch reservations and join with car details
    query = """
        SELECT reservation.id, reservation.start_date, reservation.end_date, reservation.status, 
               cars.brand, cars.model, cars.year, cars.color
        FROM reservation
        JOIN cars ON reservation.car_id = cars.id
        WHERE reservation.user_id = %s
        ORDER BY reservation.start_date DESC
    """
    cursor.execute(query, (user_id,))
    reservations = cursor.fetchall()

    cursor.close()
    connection.close()

    # Return reservations as JSON
    return jsonify(reservations)


@app.route('/add_reservation', methods=['POST'])
def add_reservation():
    if 'username' in session:
        # check the reservation first
        user_id = session['user_id']
        car_id = request.form.get('car_id')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')

        conn = get_db_connection()
        cursor = conn.cursor()
        query = """
                SELECT * FROM reservation
                WHERE user_id = %s AND status = 'confirmed'
            """
        cursor.execute(query, (user_id,))
        confirmed_reservation = cursor.fetchone()
        cursor.close()
        conn.close()

        if confirmed_reservation:
            # Redirect to the page specific for confirmed reservations
            flash("You already have one reservation now, Please cancel it first.")
            return redirect(url_for('rent_car', car_id=car_id))
        else:

            # Insert the reservation into the database
            conn = get_db_connection()
            cursor = conn.cursor()

            try:
                cursor.execute("""
                    INSERT INTO reservation (car_id, user_id, start_date, end_date, status)
                    VALUES (%s, %s, %s, %s, 'confirmed')
                """, (car_id, user_id, start_date, end_date))

                conn.commit()
                print('Reservation successful!')

            except Exception as e:
                conn.rollback()
                print(f"Error: {e}")

            finally:
                cursor.close()
                conn.close()

            # Redirect to the explore cars page after successful reservation
            return redirect(url_for('explore_cars'))

    else:
        return redirect(url_for('log_in'))


# admin
@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Validate form data
        if not (username and password):
            flash('Please fill out all fields', 'error')
            return redirect(url_for('admin_login'))

        # Authenticate user
        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
                user = cursor.fetchone()
                if user and check_password_hash(user['password_hash'], password) and user['user_type'] == 'admin':
                    print('Login successful!')
                    # Start user session
                    session.permanent = True
                    session['user_id'] = user['id']
                    session['username'] = user['username']
                    session['user_type'] = user['user_type']

                    return redirect(url_for('dashboard'))
                else:
                    flash('Invalid username or password', 'error')
            except mysql.connector.Error as err:
                print(err)
                flash('Error logging in. Please try again.', 'error')
            finally:
                cursor.close()
                conn.close()

    return render_template('log_in_admin.html')


@app.route('/dashboard')
def dashboard():
    if 'username' in session and session['user_type'] == 'admin':
        return render_template('index_admin.html')
    else:
        return redirect(url_for('admin_login'))


@app.route('/car_management')
def car_management():
    if 'username' in session and session['user_type'] == 'admin':
        return render_template('car_manage_admin.html')
    else:
        return redirect(url_for('admin_login'))


@app.route('/reservation_manage')
def reservation_manage():
    if 'username' in session and session['user_type'] == 'admin':
        return render_template('reservation_manage.html')
    else:
        return redirect(url_for('admin_login'))


@app.route('/get_all_reservations')
def get_all_reservations():
    if 'username' in session and session['user_type'] == 'admin':
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # Fetch all reservations and join with car details
        query = """
                SELECT 
                    reservation.id, 
                    reservation.start_date, 
                    reservation.end_date, 
                    reservation.status, 
                    reservation.user_id,
                    users.real_name, 
                    cars.brand, 
                    cars.model, 
                    cars.year, 
                    cars.color
                FROM reservation
                JOIN cars ON reservation.car_id = cars.id
                JOIN users ON reservation.user_id = users.id
                ORDER BY reservation.start_date DESC
            """
        cursor.execute(query)
        reservations = cursor.fetchall()

        cursor.close()
        connection.close()

        # Return reservations as JSON
        return jsonify(reservations)
    else:
        return redirect(url_for('admin_login'))


@app.route('/delete_car/<int:car_id>', methods=['DELETE'])
def delete_car(car_id):
    if 'username' in session and session['user_type'] == 'admin':
        conn = get_db_connection()
        cursor = conn.cursor()

        # Delete the car with the specific id from the database
        cursor.execute("DELETE FROM cars WHERE id = %s", (car_id,))

        conn.commit()
        cursor.close()
        conn.close()

        # Return a success message
        return jsonify({'message': 'Car deleted successfully'}), 200
    else:
        return redirect(url_for('admin_login'))


@app.route('/edit_car/<int:car_id>', methods=['GET'])
def edit_car(car_id):
    if 'username' in session and session['user_type'] == 'admin':
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Fetch the car details
        cursor.execute("SELECT * FROM cars WHERE id = %s", (car_id,))
        car = cursor.fetchone()

        cursor.close()
        conn.close()

        if car:
            # Convert the BLOB to a base64 string to send to the frontend
            car_image = base64.b64encode(car['picture']).decode('utf-8') if car['picture'] else None
            return render_template('edit_car.html', car=car, car_image=car_image)
        else:
            flash("Car not found.")
            return redirect(url_for('car_management'))
    else:
        return redirect(url_for('admin_login'))


@app.route('/update_car/<int:car_id>', methods=['POST'])
def update_car(car_id):
    if 'username' in session and session['user_type'] == 'admin':
        brand = request.form['brand']
        model = request.form['model']
        year = request.form['year']
        color = request.form.get('color', None)
        capacity = request.form['capacity']
        car_type = request.form['type']
        transmission = request.form['transmission']
        consumption = request.form['consumption']
        power = request.form['power']
        price = request.form['price']

        # Handle file upload for car image
        if 'picture' in request.files:
            picture_file = request.files['picture']
            picture_data = picture_file.read() if picture_file.filename != '' else None
        else:
            picture_data = None

        conn = get_db_connection()
        cursor = conn.cursor()

        if picture_data:
            # Update car details and image
            update_query = """
            UPDATE cars 
            SET brand = %s, model = %s, year = %s, color = %s, capacity = %s, 
                type = %s, transmission = %s, consumption = %s, power = %s, price = %s, picture = %s
            WHERE id = %s
            """
            cursor.execute(update_query, (
                brand, model, year, color, capacity, car_type, transmission, consumption, power, price, picture_data,
                car_id))
        else:
            # Update car details without image
            update_query = """
            UPDATE cars 
            SET brand = %s, model = %s, year = %s, color = %s, capacity = %s, 
                type = %s, transmission = %s, consumption = %s, power = %s, price = %s
            WHERE id = %s
            """
            cursor.execute(update_query,
                           (brand, model, year, color, capacity, car_type, transmission, consumption, power, price, car_id))

        conn.commit()
        cursor.close()
        conn.close()

        flash("Car updated successfully!")
        return redirect(url_for('car_management'))
    else:
        return redirect(url_for('admin_login'))


@app.route('/new_car')
def new_car():
    if 'username' in session and session['user_type'] == 'admin':
        return render_template('new_car.html')
    else:
        return redirect(url_for('admin_login'))


@app.route('/add_car', methods=['POST'])
def add_car():
    if 'username' in session and session['user_type'] == 'admin':
        brand = request.form['brand']
        model = request.form['model']
        year = request.form['year']
        color = request.form.get('color', None)
        capacity = request.form['capacity']
        car_type = request.form['type']
        transmission = request.form['transmission']
        consumption = request.form['consumption']
        power = request.form['power']
        price = request.form['price']

        # Handle file upload for car image
        if 'picture' in request.files:
            picture_file = request.files['picture']
            picture_data = picture_file.read() if picture_file.filename != '' else None
        else:
            picture_data = None

        conn = get_db_connection()
        cursor = conn.cursor()

        insert_query = """
        INSERT INTO cars (brand, model, year, color, capacity, type, transmission, consumption, power, price, picture)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(insert_query, (
            brand, model, year, color, capacity, car_type, transmission, consumption, power, price, picture_data
        ))

        conn.commit()
        cursor.close()
        conn.close()

        flash("Car added successfully!")
        return redirect(url_for('car_management'))
    else:
        return redirect(url_for('admin_login'))


@app.route('/edit_reservation/<int:reservation_id>', methods=['GET'])
def edit_reservation(reservation_id):
    if 'username' in session and session['user_type'] == 'admin':
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Fetch reservation details
        cursor.execute("SELECT * FROM reservation WHERE id = %s", (reservation_id,))
        reservation = cursor.fetchone()

        # Fetch list of cars
        cursor.execute("SELECT * FROM cars")
        cars = cursor.fetchall()

        # Fetch the number of confirmed reservations for the user
        cursor.execute("SELECT user_id FROM reservation WHERE id = %s", (reservation_id,))
        user_id = cursor.fetchone()['user_id']
        cursor.execute("SELECT COUNT(*) AS confirmed_count FROM reservation WHERE user_id = %s AND status = 'Confirmed'", (user_id,))
        confirmed_count = cursor.fetchone()['confirmed_count']

        cursor.close()
        conn.close()

        if reservation:
            return render_template('edit_reservation.html', reservation=reservation, cars=cars, confirmed_count=confirmed_count)
        else:
            flash("Reservation not found.")
            return redirect(url_for('reservation_manage'))
    else:
        return redirect(url_for('admin_login'))

@app.route('/update_reservation/<int:reservation_id>', methods=['POST'])
def update_reservation(reservation_id):
    if 'username' in session and session['user_type'] == 'admin':
        car_id = request.form['car_id']
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        status = request.form['status']

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Fetch the user_id from the reservation being edited
        cursor.execute("SELECT user_id FROM reservation WHERE id = %s", (reservation_id,))
        reservation = cursor.fetchone()

        if reservation:
            user_id = reservation['user_id']

            # Check if the user already has a confirmed reservation
            if status == 'Confirmed':
                cursor.execute("SELECT COUNT(*) AS confirmed_count FROM reservation WHERE user_id = %s AND status = 'Confirmed'", (user_id,))
                confirmed_count = cursor.fetchone()['confirmed_count']

                if confirmed_count > 0:
                    flash("This user already has a confirmed reservation. Please cancel or modify the existing one before confirming a new reservation.")
                    cursor.close()
                    conn.close()
                    return redirect(url_for('edit_reservation', reservation_id=reservation_id))

            # Proceed with updating the reservation
            update_query = """
            UPDATE reservation
            SET car_id = %s, start_date = %s, end_date = %s, status = %s
            WHERE id = %s
            """
            cursor.execute(update_query, (car_id, start_date, end_date, status, reservation_id))

            conn.commit()
            cursor.close()
            conn.close()

            flash("Reservation updated successfully!")
        else:
            flash("Reservation not found.")

        return redirect(url_for('reservation_manage'))
    else:
        return redirect(url_for('admin_login'))


if __name__ == '__main__':
    app.run(debug=True)
