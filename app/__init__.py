from flask import Flask, request
from flask_svelte import render_template
import sqlite3
import uuid
import json
import time
import threading
from pywebpush import webpush

app = Flask(__name__)

SQLITE_DB_PATH = "database.db"
USER_PING_COOLDOWN = 3

with open("keys.json", "r") as f:
    j = json.load(f)

    PRIVATE_KEY = j["private"]
    PUBLIC_KEY = j["public"]

db_thread_lock = threading.Lock()
ping_processing_lock = threading.Lock()

def connect_db():
    db_thread_lock.acquire(timeout=3)

    conn = sqlite3.connect(SQLITE_DB_PATH)
    cursor = conn.cursor()

    return conn, cursor

def disconnect_db(conn):
    conn.close()
    db_thread_lock.release()

def create_db_tables():
    conn, cursor = connect_db()

    #Create tables if they don't exist already
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    country TEXT,
                    notification_subscription TEXT,
                    next_allowed_ping_timestamp INTEGER
                  )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS pings (
                    id TEXT PRIMARY KEY,
                    from_user TEXT,
                    to_user TEXT,
                    reply_to TEXT,
                    display_country_of_origin BOOLEAN,
                    timestamp INTEGER,
                    state TEXT,
                    FOREIGN KEY(from_user) REFERENCES users(id),
                    FOREIGN KEY(to_user) REFERENCES users(id),
                    FOREIGN KEY(reply_to) REFERENCES pings(id)
                  )''')

    conn.commit()
    disconnect_db(conn)

def create_ping(from_user, to_user=None, reply_to=None, display_country_of_origin=True, ignore_multiple_replies=False, ignore_user_ping_cooldown=False):
    conn, cursor = connect_db()

    #In case of a reply, check that the original ping wasn't already replied to and specify to_user
    if reply_to:
        cursor.execute("SELECT COUNT(*) FROM pings WHERE reply_to = ?", (reply_to,))
        count = cursor.fetchone()[0]
        
        #The original ping was already replied to
        if count >= 1 and not ignore_multiple_replies:
            disconnect_db(conn)
            return {"ok": False, "error": "You have already replied to this ping."}
        
        #Find the target user's id
        cursor.execute("SELECT from_user FROM pings WHERE id = ?", (reply_to,))
        to_user = cursor.fetchone()[0]

    #Check if the sending user can send a ping (that they aren't on cooldown)
    cursor.execute("SELECT next_allowed_ping_timestamp FROM users WHERE id = ?", (from_user,))
    next_allowed_ping_timestamp = cursor.fetchone()[0]

    if next_allowed_ping_timestamp > time.time() and not ignore_user_ping_cooldown:
        disconnect_db(conn)
        return {"ok": False, "error": f"You must wait before sending another ping. ({round(next_allowed_ping_timestamp - time.time())}s)"}

    #Select a random to_user if not specified
    if not to_user:
        cursor.execute("SELECT id FROM users ORDER BY RANDOM() LIMIT 1")
        to_user = cursor.fetchone()[0]

    #Create the ping
    ping_id = uuid.uuid4().hex
    cursor.execute("INSERT INTO pings (id, from_user, to_user, reply_to, display_country_of_origin, timestamp, state) VALUES (?, ?, ?, ?, ?, ?, ?)", (ping_id, from_user, to_user, reply_to, display_country_of_origin, int(time.time()), "waiting"))

    #Update user's next_allowed_ping_timestamp
    cursor.execute("UPDATE users SET next_allowed_ping_timestamp = ? WHERE id = ?", (int(time.time() + USER_PING_COOLDOWN), from_user))

    #Disconnect from the database
    conn.commit()
    disconnect_db(conn)

    #Start a new thread to process the ping
    threading.Thread(target=process_waiting_pings).start()

    return {"ok": True}

def process_waiting_pings():
    ping_processing_lock.acquire(timeout=5*60)

    #Get list of waiting pings, and for each the origin user's country and target user's notification subscription object
    conn, cursor = connect_db()

    cursor.execute("SELECT pings.id, from_users.country, pings.display_country_of_origin, pings.reply_to, users.notification_subscription FROM pings INNER JOIN users ON pings.to_user = users.id INNER JOIN users AS from_users ON pings.from_user = from_users.id WHERE pings.state = 'waiting'")
    pings = cursor.fetchall()
    
    disconnect_db(conn)
    
    for ping in pings:
        ping_id, country_of_origin, display_country_of_origin, reply_to, notification_subscription = ping

        #Try to send the notification
        try:
            ping_text = generate_ping_text(display_country_of_origin, country_of_origin, is_reply=bool(reply_to))
            
            #Send the data
            data = {
                "id": ping_id,
                "text": ping_text
            }

            print(f"Sending ping {ping_id}")
            #webpush(subscription_info=json.loads(notification_subscription), data=json.dumps(data), ttl=30*60, vapid_private_key=PRIVATE_KEY, vapid_claims={"sub":"mailto:dev@example.com"})
            print(f"Sent ping {ping_id}")

            state = "success"
        except Exception as e:
            print(e)
            state = "failed"

        #Update ping's state in DB
        conn, cursor = connect_db()

        cursor.execute("UPDATE pings SET state = ? WHERE id = ?", (state, ping_id))
        conn.commit()
        disconnect_db(conn)

    ping_processing_lock.release()

def generate_ping_text(display_country_of_origin, country_of_origin, is_reply):
    if is_reply: #Never reveal country of origin in a reply
        return "Somebody pinged you back!"
    
    if display_country_of_origin:
        return f"Somebody from {country_of_origin} pinged you!"
    else:
        return "Somebody pinged you!"

# --------------------------------------------------------------------------- #

@app.route('/')
def index():
    return render_template('index.html', name='World')

@app.get("/info")
def get_info():
    return {"public_key": PUBLIC_KEY, "ping_cooldown": USER_PING_COOLDOWN}

@app.post("/user/register")
def post_user_register():
    #Random user ID
    user_id = uuid.uuid4().hex

    #Get the user's country of origin
    #TODO: IMPLEMENT
    country = "US" 

    #Connect to DB
    conn, cursor = connect_db()

    #Commit to and close DB
    cursor.execute("INSERT INTO users (id, country, next_allowed_ping_timestamp) VALUES (?, ?, ?)", (user_id, country, 0))
    conn.commit()
    disconnect_db(conn)

    #Send back user information
    return {"user_id": user_id, "country": country}

@app.post("/user/update_notification_subscription_object")
def post_user_update_notification_subscription_object():
    data = request.json

    user_id = uuid.UUID(data["user_id"]).hex
    subscription = data["subscription"] #TODO: Validate subscription object! (This is the only place we accept completly user-generated data)

    #Connect to DB
    conn, cursor = connect_db()

    #Update the DB
    cursor.execute("UPDATE users SET notification_subscription = ? WHERE id = ?", (json.dumps(subscription), user_id))
    conn.commit()
    disconnect_db(conn)

    return {"ok": True}

@app.post("/ping/random")
def post_ping_random():
    data = request.json

    from_user = uuid.UUID(data["user_id"]).hex
    return create_ping(from_user)

@app.post("/ping/reply")
def post_ping_reply():
    data = request.json

    from_user = uuid.UUID(data["user_id"]).hex
    reply_to = uuid.UUID(data["reply_to"]).hex

    return create_ping(from_user, reply_to=reply_to)

if __name__ == "__main__":
    create_db_tables()

    app.run(host="0.0.0.0", port=5000, threaded=True, debug=True)