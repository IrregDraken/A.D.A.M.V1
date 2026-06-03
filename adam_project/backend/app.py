from flask import Flask, request, jsonify
from database import init_db, get_connection
from rules import analyze_event
from telegram_bot import send_alert_with_buttons

app = Flask(__name__)

init_db()


def save_event(event, analysis):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO events (
            device_id,
            sensor_type,
            value,
            location,
            timestamp,
            anomaly,
            risk_level,
            action_taken,
            confidence_score,
            decision_basis
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        event["device_id"],
        event["sensor_type"],
        str(event["value"]),
        event["location"],
        event["timestamp"],
        analysis["anomaly"],
        analysis["risk_level"],
        analysis["action_taken"],
        analysis["confidence_score"],
        analysis["decision_basis"]
    ))

    event_id = cursor.lastrowid

    if analysis["anomaly"] == 1:

        cursor.execute("""
            INSERT INTO alerts (
                event_id,
                alert_message,
                created_at,
                status
            )
            VALUES (?, ?, ?, ?)
        """, (
            event_id,
            analysis["reason"],
            event["timestamp"],
            "pending"
        ))

        alert_id = cursor.lastrowid

        message = (
            f"🚨 ADAM SECURITY ALERT #{alert_id}\n"
            f"Device: {event['device_id']}\n"
            f"Sensor: {event['sensor_type']}\n"
            f"Location: {event['location']}\n"
            f"Value: {event['value']}\n"
            f"Risk: {analysis['risk_level'].upper()}\n"
            f"Confidence: {int(analysis['confidence_score'] * 100)}%\n"
            f"Reason: {analysis['reason']}\n"
            f"Decision Basis: {analysis['decision_basis']}\n"
            f"Time: {event['timestamp']}\n"
            f"Status: PENDING\n"
            f"Action: {analysis['action_taken']}"
        )

        try:
            tg_response = send_alert_with_buttons(message)

            telegram_message_id = tg_response["result"]["message_id"]

            cursor.execute("""
                UPDATE alerts
                SET telegram_message_id = ?
                WHERE id = ?
            """, (
                str(telegram_message_id),
                alert_id
            ))

        except Exception as e:
            print("Telegram Error:", e)

    conn.commit()
    conn.close()


def create_command(device_id, command):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO commands (
            device_id,
            command
        )
        VALUES (?, ?)
    """, (
        device_id,
        command
    ))

    conn.commit()
    conn.close()


def get_pending_command(device_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM commands
        WHERE device_id = ?
        AND status = 'pending'
        ORDER BY id ASC
        LIMIT 1
    """, (device_id,))

    command = cursor.fetchone()

    if command:
        cursor.execute("""
            UPDATE commands
            SET status = 'executed'
            WHERE id = ?
        """, (command["id"],))

        conn.commit()

    conn.close()

    return command


@app.route("/")
def home():
    return jsonify({
        "message": "A.D.A.M backend is running"
    })


@app.route("/event", methods=["POST"])
def receive_event():

    event = request.get_json()

    required_fields = [
        "device_id",
        "sensor_type",
        "value",
        "location",
        "timestamp"
    ]

    for field in required_fields:
        if field not in event:
            return jsonify({
                "error": f"Missing field: {field}"
            }), 400

    analysis = analyze_event(event)

    save_event(event, analysis)

    return jsonify({
        "event": event,
        "analysis": analysis,
        "message": "Event processed and saved successfully"
    })


@app.route("/events", methods=["GET"])
def get_events():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM events
        ORDER BY id DESC
    """)

    rows = cursor.fetchall()

    conn.close()

    return jsonify([dict(row) for row in rows])


@app.route("/alerts", methods=["GET"])
def get_alerts():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM alerts
        ORDER BY id DESC
    """)

    rows = cursor.fetchall()

    conn.close()

    return jsonify([dict(row) for row in rows])


@app.route("/command", methods=["POST"])
def command():

    data = request.get_json()

    create_command(
        data["device_id"],
        data["command"]
    )

    return jsonify({
        "message": "Command queued"
    })


@app.route("/commands/<device_id>", methods=["GET"])
def fetch_command(device_id):

    cmd = get_pending_command(device_id)

    if cmd:
        return jsonify({
            "command": cmd["command"]
        })

    return jsonify({
        "command": None
    })

@app.route("/commands")
def view_commands():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM commands
        ORDER BY id DESC
    """)

    rows = cursor.fetchall()

    conn.close()

    return jsonify([
        dict(row)
        for row in rows
    ])

if __name__ == "__main__":
    app.run(debug=True)