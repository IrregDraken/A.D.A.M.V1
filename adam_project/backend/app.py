from flask import Flask, request, jsonify
from database import init_db, get_connection
from rules import analyze_event
from telegram_bot import send_telegram_message, send_alert_with_buttons

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
            INSERT INTO alerts (event_id, alert_message, created_at, status)
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
            """, (str(telegram_message_id), alert_id))

        except Exception as e:
            print("Telegram error:", e)

    conn.commit()
    conn.close()

@app.route("/")
def home():
    return jsonify({"message": "A.D.A.M backend is running"})


@app.route("/event", methods=["POST"])
def receive_event():
    event = request.get_json()

    required_fields = ["device_id", "sensor_type", "value", "location", "timestamp"]
    for field in required_fields:
        if field not in event:
            return jsonify({"error": f"Missing field: {field}"}), 400

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
    cursor.execute("SELECT * FROM events ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()

    events = [dict(row) for row in rows]
    return jsonify(events)


@app.route("/alerts", methods=["GET"])
def get_alerts():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM alerts ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()

    alerts = [dict(row) for row in rows]
    return jsonify(alerts)

@app.route("/command", methods=["POST"])
def create_command():
    data = request.get_json()

    device_id = data.get("device_id")
    command = data.get("command")

    if not device_id or not command:
        return jsonify({"error": "Missing device_id or command"}), 400

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO commands (device_id, command) VALUES (?, ?)",
        (device_id, command)
    )

    conn.commit()
    conn.close()

    return jsonify({"success": True})

@app.route("/commands/<device_id>", methods=["GET"])
def get_pending_command(device_id):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM commands
        WHERE device_id = ?
        AND status = 'pending'
        ORDER BY id ASC
        LIMIT 1
    """, (device_id,))

    row = cursor.fetchone()

    if not row:
        conn.close()
        return jsonify({"command": None})

    cursor.execute(
        "UPDATE commands SET status = 'sent' WHERE id = ?",
        (row["id"],)
    )

    conn.commit()
    conn.close()

    return jsonify({
        "id": row["id"],
        "command": row["command"]
    })
if __name__ == "__main__":
    app.run(debug=True)