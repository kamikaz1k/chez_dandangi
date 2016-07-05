from flask import Flask, render_template, json, request, redirect, session, url_for, jsonify
from flask.ext.mysql import MySQL
from werkzeug import generate_password_hash, check_password_hash
from datetime import datetime

# from pprint import pprint

# App Configurations
app = Flask(__name__)

# Load config file for DB user info
with open("config.json") as data_file: 
    config = json.load(data_file)

# Set secret key to use the session module
app.secret_key = config["secret_key"]

# MySQL configurations
app.config["MYSQL_DATABASE_USER"] = config["username"]
app.config["MYSQL_DATABASE_PASSWORD"] = config["password"]
app.config["MYSQL_DATABASE_DB"] = "chez_dandangi"
app.config["MYSQL_DATABASE_HOST"] = "localhost"

mysql = MySQL()
mysql.init_app(app)

# Routing Definitions
@app.route("/")
def main():
    return render_template("index.html")

@app.route("/getReservations", methods=['POST'])
def get_reservations():

    # read the posted values from the UI
    _date = request.form['search-date']

    print "The Search Data: ", request.form, _date

    if _date:
        return redirect('/listReservations/' + _date)
        # return redirect(url_for('list_reservations' + _date))
    else:
        return json.dumps('message', 'No Date?')

@app.route("/listReservations/<mon>/<day>/<year>")
def list_reservations(mon, day, year):

    print "Get reservations for: ", mon, day, year
    reservations = []
    _date = "/".join([mon, day, year])

    if _date:
        # Wrap db calls in try/except/finally
        try:
            # Connect to DB
            conn = mysql.connect()

            # Retrieve DB Cursor
            cursor = conn.cursor()

            # Make query
            cursor.callproc('sp_getReservations', (_date + " 00:00", _date + " 23:59"))
            data = cursor.fetchall()

            print "Cursor: ", data
            # print "STR: ", jsonify(data)
             
            # if len(data) is 0:
            #     # Commit changes to db
            #     conn.commit()
            #     return json.dumps({'message':'User created successfully !'})
            # else:
            #     print "Username already exists? - ", data
            #     return json.dumps({'error':str(data[0])})
            # conn.commit()

            # reservations = json.dumps(data)
            # for entry in data:
            #     print entry
            #     entry = entry["customer_name"] + entry["customer_contact"]
            
            reservations = data

        # Catch any exceptions
        except Exception as e:
            return json.dumps({'error':str(e)})

        # Finally close cursor & connection so that next 
        # transaction can take place separately
        finally:
            cursor.close()
            conn.close()

    else:
        print "There was no date?"

    # Pad the outstanding reservation times
    # TODO: Dynamically create dictionary based on the tables listed in DB
    tables = { "1": [], "2": [] }
    tables["1"] = reservation_list_builder(int(year), int(mon), int(day), 1);
    tables["2"] = reservation_list_builder(int(year), int(mon), int(day), 2);

    # Replace reservations with retrieved ones
    for table_id in tables:
        items = tables[table_id]
        # loop through reservations and replace reservations
        for item in reservations:
            # item[1] is the table_id field
            if item[1] == int(table_id):
                i = item[2].hour
                items[i] = item

    # print "tables: ", tables

    return render_template('list_reservations.html', tables = tables, date = _date)

@app.route("/showReservationPage")
@app.route("/showReservationPage/")
@app.route("/showReservationPage/<mon>/<day>/<year>/<hr>/<mm>/<table>")
def show_reservation_page(mon = "", day = "", year = "", hr = "", mm = "", table = ""):
    # Generate default values for form
    if mon and day and year:
        date = "/".join([mon, day, year])
    else:
        date = ""

    if hr and mm:
        time = ":".join([hr, mm])
    else:
        time = ""

    return render_template('create_reservation.html', date = date, time = time, table = table)

@app.route("/createReservation", methods=['POST'])
def create_reservation():

    _name = request.form['inputName']
    _date = request.form['inputDate']
    _time = request.form['inputTime']
    _table = request.form['inputTable']
    _contact = request.form['inputContact']
    _size = request.form['inputSize']

    if _name and _date and _time and _table and _size:

        # TODO: Verify _name and _date and _time
        # print "Form:", _name, _date, _time, _contact, str(_size)
        
        try:
            # Connect to DB
            conn = mysql.connect()

            # Retrieve DB Cursor
            cursor = conn.cursor()

            # Make query
            cursor.callproc('sp_createReservation',(_table, _date + _time, _date + _time.split(":")[0] + ":59", _name, _contact, _size))
            data = cursor.fetchall()
            
            # If nothing is returned then creation was a success
            if len(data) is 0:
                # Commit changes to db
                conn.commit()
                # return json.dumps({'message':'Reservation Created!'})
                return redirect('/listReservations/' + _date)
            else:
                # print "Username already exists? - ", data
                return json.dumps({ 'error': str(data[0]) })
     
        except Exception as e:
            return render_template('error.html', error = str(e))

        # Finally close cursor & connection so that next 
        # transaction can take place separately
        finally:
            cursor.close()
            conn.close()

    # IF the signup form fields were not populated
    else:
        return json.dumps({'html':'<span>Enter the required fields</span>'})

    # return json.dumps({'html':'<span>Reservation Made!</span>'})

@app.errorhandler(404)
def page_not_found(error):
    return render_template("page_not_found.html"), 404

def reservation_list_builder(year, mon, day, table_id):
    items = []
    for hr in range(23):
        item = [] 
        item.append("") # Row ID
        item.append(table_id) # Table ID
        item.append(datetime(year, mon, day, hr, 0)) # Start Time
        item.append(datetime(year, mon, day, hr + 1, 0)) # End Time
        item.append("") # Holder
        item.append("") # Contact
        items.append(item)

    # Last hr
    item = [] 
    item.append("") # Row ID
    item.append(table_id) # Table ID
    item.append(datetime(year, mon, day, 23, 0)) # Start Time
    item.append(datetime(year, mon, day, 23, 59)) # End Time
    item.append("") # Holder
    item.append("") # Contact
    items.append(item)

    return items

# Run app    
if __name__ == "__main__":
    app.run()