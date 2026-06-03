if sensor_type == "motion":

    if value == "1":

        if location in [
            "lab",
            "server_room",
            "office",
            "oil_mill"
        ]:

            anomaly = 1
            risk_level = "high"
            action_taken = "send_alert"
            reason = "Motion detected in protected area"
            confidence_score = 0.92
            decision_basis = "Protected-area motion detection"

        elif location == "hallway":

            anomaly = 0
            risk_level = "low"
            action_taken = "log_only"
            reason = "Hallway motion is considered safe"
            confidence_score = 0.78
            decision_basis = "Expected motion zone"

        else:

            anomaly = 0
            risk_level = "low"
            action_taken = "log_only"
            reason = "Normal motion event"
            confidence_score = 0.72
            decision_basis = "Motion detected in non-sensitive context"