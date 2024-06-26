from flask import Flask, request, send_file
from flask_svelte import render_template
import sqlite3
import uuid
import json
import time
import threading
from pywebpush import webpush

#For offline IP geolocation
import geoacumen
import maxminddb

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
                    creation_finalized BOOLEAN,
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

def create_account(country, creation_finalized=False):
    #Random user ID
    user_id = uuid.uuid4().hex

    #Connect to DB
    conn, cursor = connect_db()

    #Commit to and close DB
    cursor.execute("INSERT INTO users (id, creation_finalized, country, next_allowed_ping_timestamp) VALUES (?, ?, ?, ?)", (user_id, creation_finalized, country, 0))
    conn.commit()
    disconnect_db(conn)

    return {"user_id": user_id, "country": {"iso": country, "emoji": country_iso_code_to_emoji(country)}}

def delete_account(user_id):
    conn, cursor = connect_db()
    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    disconnect_db(conn)
    print(f"Deleted account {user_id}")

def create_ping(from_user, to_user=None, reply_to=None, display_country_of_origin=True, ignore_multiple_replies=False, ignore_user_ping_cooldown=False):
    conn, cursor = connect_db()

    #In case of a reply, check that the original ping wasn't already replied to and specify to_user
    try:
        if reply_to:
            cursor.execute("SELECT COUNT(*) FROM pings WHERE reply_to = ?", (reply_to,))
            count = cursor.fetchone()[0]
            
            #The original ping was already replied to
            if count >= 1 and not ignore_multiple_replies:
                disconnect_db(conn)
                raise Exception("You have already replied to this ping.")
            
            #Find the target user's id
            cursor.execute("SELECT from_user FROM pings WHERE id = ?", (reply_to,))
            to_user = cursor.fetchone()[0]
    except Exception as e:
        disconnect_db(conn)
        raise Exception(f"Failed to find ping information: {Exception}")

    #Check if the sending user can send a ping (that they aren't on cooldown)
    try:
        cursor.execute("SELECT next_allowed_ping_timestamp FROM users WHERE creation_finalized = TRUE AND id = ?", (from_user,))
        next_allowed_ping_timestamp = cursor.fetchone()[0]
    except Exception as e:
        disconnect_db(conn)
        raise Exception(f"Failed to load user information ({e}). Please try deleting and creating your account again if needed.")

    if next_allowed_ping_timestamp > time.time() and not ignore_user_ping_cooldown:
        disconnect_db(conn)
        raise Exception(f"You must wait before sending another ping. ({round(next_allowed_ping_timestamp - time.time())}s)")

    #Select a random to_user if not specified
    if not to_user:
        cursor.execute("SELECT id FROM users WHERE creation_finalized = TRUE ORDER BY RANDOM() LIMIT 1")
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

def process_waiting_pings():
    ping_processing_lock.acquire(timeout=5*60)

    #Get list of waiting pings, and for each the origin user's country
    conn, cursor = connect_db()

    cursor.execute("SELECT pings.id, pings.to_user, from_users.country, pings.display_country_of_origin, pings.reply_to FROM pings INNER JOIN users AS from_users ON pings.from_user = from_users.id WHERE pings.state = 'waiting'")
    pings = cursor.fetchall()
    
    disconnect_db(conn)
    
    for ping in pings:
        ping_id, to_user, country_of_origin, display_country_of_origin, reply_to = ping

        #Try to send the notification
        try:
            ping_text = generate_ping_text(display_country_of_origin, country_of_origin, is_reply=bool(reply_to))
            
            #Send the data
            data = {
                "title": "Random ping received!",
                "options": {
                    "id": ping_id,
                    "body": ping_text,
                    "requireInteraction": True,
                    "vibrate": [300, 100, 400],
                    "actions": [
                        {
                            "action": "reply",
                            "title": "Ping back!"
                        }
                    ],
                    "data": {
                        "url": f"/#{ping_id}"
                    }
                }
            }

            print(f"Sending ping {ping_id}")
            send_notification(to_user, data)
            print(f"Sent ping {ping_id}")

            state = "success"
        except Exception as e:
            print(e)
            state = "failed"

            #Delete the account
            delete_account(to_user)

        #Update ping's state in DB
        conn, cursor = connect_db()

        cursor.execute("UPDATE pings SET state = ? WHERE id = ?", (state, ping_id))
        conn.commit()
        disconnect_db(conn)

    ping_processing_lock.release()

def send_notification(user_id, data, ttl=30*60):
    #Get the user's notification subscription object
    conn, cursor = connect_db()
    cursor.execute("SELECT notification_subscription FROM users WHERE id = ?", (user_id,))
    subscription = cursor.fetchone()[0]
    disconnect_db(conn)

    #Send the notification
    webpush(subscription_info=json.loads(subscription), data=json.dumps(data), ttl=ttl, vapid_private_key=PRIVATE_KEY, vapid_claims={"sub":"mailto:dev@example.com"})

def locate_ip_country(ip_address):
    try:
        reader = maxminddb.open_database(geoacumen.db_path)
        location = reader.get(ip_address)

        if not location["country"]["iso_code"]:
            return None

        return location["country"]["iso_code"].upper()
    except Exception as e:
        print(f"Failed to locate ip: {ip_address}")
        return None

def country_iso_code_to_emoji(country_iso_code):
    #Invalid ISO code
    if not country_iso_code or len(country_iso_code) != 2 or not country_iso_code.isalpha():
        return "❔"
    
    country_iso_code = country_iso_code.upper()
    OFFSET = ord('🇦') - ord('A')
    
    emoji_sequence = ''.join(chr(ord(c) + OFFSET) for c in country_iso_code)
    return emoji_sequence

def generate_ping_text(display_country_of_origin, country_of_origin, is_reply):
    if is_reply: #Never reveal country of origin in a reply
        return "Somebody has pinged you back! Click to ping them back again!"
    
    if display_country_of_origin:
        return f"Somebody from {country_iso_code_to_emoji(country_of_origin)} has pinged you! Click to ping them back"
    else:
        return "Somebody has pinged you! Click to ping them back"

# --------------------------------------------------------------------------- #

@app.get('/')
def get_index():
    return render_template("index.html")

@app.get("/sw.js")
def get_service_worker():
    return send_file("static/service-worker.js")

@app.get("/info")
def get_info():
    return {"public_key": PUBLIC_KEY, "ping_cooldown": USER_PING_COOLDOWN}

@app.post("/user/register")
def post_user_register():
    #Get the user's country of origin
    country = locate_ip_country(request.remote_addr)

    #Create account and send back its information
    return create_account(country)

@app.post("/user/delete")
def post_user_delete():
    data = request.json
    user_id = uuid.UUID(data["user_id"]).hex
    
    delete_account(user_id)

    return {"ok": True}

@app.post("/user/update_notification_subscription_object")
def post_user_update_notification_subscription_object():
    data = request.json

    user_id = uuid.UUID(data["user_id"]).hex
    subscription = dict(data["subscription"]) #NOTE: This is the only place we accept completly user-generated data)

    #Make sure the subscription object isn't too long
    if len(json.dumps(subscription)) > 1200:
        return {"ok": False, "error": f"Subscription object too long. ({len(json.dumps(subscription))})"}

    #Connect to DB
    conn, cursor = connect_db()

    #Update the DB
    cursor.execute("UPDATE users SET notification_subscription = ? WHERE id = ?", (json.dumps(subscription), user_id))
    conn.commit()
    disconnect_db(conn)

    #Check amount of changed rows (should be 1)
    if cursor.rowcount != 1:
        return {"ok": False}

    return {"ok": True}

@app.post("/user/finalize_creation")
def post_user_finalize_creation():
    data = request.json
    user_id = uuid.UUID(data["user_id"]).hex

    #Finalize the account creation process by sending a test notification
    #to check everyting works.
    try:
        data = {
            "title": "Hello, world! 👋",
            "options": {
                "body": "Welcome! This is what pings from other users will look like."
            }
        }

        send_notification(user_id, data)
    except Exception as e:
        return {"ok": False, "error": "Failed to send initial testing notification. Please try again later."}

    #Great! Save the finalized state to the DB
    conn, cursor = connect_db()
    cursor.execute("UPDATE users SET creation_finalized = TRUE WHERE id = ?", (user_id,))
    conn.commit()
    disconnect_db(conn)

    return {"ok": True}

@app.post("/ping/random")
def post_ping_random():
    data = request.json

    from_user = uuid.UUID(data["user_id"]).hex
    display_country_of_origin = bool(data["display_country_of_origin"])

    try:
        create_ping(from_user, display_country_of_origin=display_country_of_origin)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.post("/ping/reply")
def post_ping_reply():
    data = request.json

    from_user = uuid.UUID(data["user_id"]).hex
    reply_to = uuid.UUID(data["reply_to"]).hex

    try:
        create_ping(from_user, reply_to=reply_to)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}

if __name__ == "__main__":
    create_db_tables()

    app.run(host="0.0.0.0", port=5000, threaded=True, debug=True)