from flask import Flask, request
import sqlite3
import uuid
import json
import time

app = Flask(__name__)

SQLITE_DB_PATH = "database.db"
USER_PING_TIMEOUT = 3

def connect_db():
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cursor = conn.cursor()

    return conn, cursor

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
                    timestamp INTEGER,
                    state TEXT,
                    FOREIGN KEY(from_user) REFERENCES users(id),
                    FOREIGN KEY(to_user) REFERENCES users(id),
                    FOREIGN KEY(reply_to) REFERENCES pings(id)
                  )''')

    conn.commit()
    conn.close()

def create_ping(from_user, to_user=None, reply_to=None, ignore_user_ping_timeout=False):
    conn, cursor = connect_db()

    #Check if the sending user can indeed send a ping
    cursor.execute("SELECT next_allowed_ping_timestamp FROM users WHERE id = ?", (from_user,))
    next_allowed_ping_timestamp = cursor.fetchone()[0]

    if next_allowed_ping_timestamp > time.time():
        conn.close()
        return {"ok": False, "error": f"You must wait before sending another ping. ({round(next_allowed_ping_timestamp - time.time())}s)"}

    #Select a random to_user if not specified
    if not to_user:
        cursor.execute("SELECT id FROM users ORDER BY RANDOM() LIMIT 1")
        to_user = cursor.fetchone()[0]

    #Create the ping
    ping_id = uuid.uuid4().hex
    cursor.execute("INSERT INTO pings (id, from_user, to_user, reply_to, timestamp, state) VALUES (?, ?, ?, ?, ?, ?)", (ping_id, from_user, to_user, reply_to, int(time.time()), "waiting"))

    #Update user's next_allowed_ping_timestamp
    cursor.execute("UPDATE users SET next_allowed_ping_timestamp = ? WHERE id = ?", (int(time.time() + USER_PING_TIMEOUT), from_user))

    conn.commit()
    conn.close()

    return {"ok": True}

# --------------------------------------------------------------------------- #

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
    conn.close()

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
    conn.close()

    return {"ok": True}

@app.post("/ping/random")
def post_ping_random():
    data = request.json

    from_user = uuid.UUID(data["user_id"]).hex
    return create_ping(from_user)

if __name__ == "__main__":
    create_db_tables()
    app.run(host="0.0.0.0", port=5000, threaded=True, debug=True)