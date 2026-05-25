# serial_worker.py
import time
import config

def serial_read_thread():
    while True:
        if config.ser is None or not config.ser.is_open:
            time.sleep(0.2)
            continue
            
        try:
            if config.ser.in_waiting > 0:
                line = config.ser.readline().decode('utf-8', errors='ignore').strip()
                if not line:
                    continue
                
                if config.is_stream_paused:
                    continue

                parts = line.split(',')
                if len(parts) >= 18:
                    current_unix = time.time()
                    
                    if config.launch_time is not None:
                        current_timestamp = current_unix - config.launch_time
                    else:
                        current_timestamp = current_unix - config.start_time
                    
                    x_pos, y_pos, z_pos = float(parts[0]), float(parts[1]), float(parts[2])
                    x_vel, y_vel, z_vel = float(parts[3]), float(parts[4]), float(parts[5])
                    x_acc, y_acc, z_acc = float(parts[6]), float(parts[7]), float(parts[8])
                    pitch, roll, yaw    = float(parts[9]), float(parts[10]), float(parts[11])
                    alt, temp           = float(parts[12]), float(parts[13])
                    
                    raw_tx_mode = parts[14].strip()
                    raw_rx_mode = parts[15].strip()
                    
                    # --- TX FLIGHTSTATE ENUM MAP ---
                    if raw_tx_mode == "0":
                        tx_string = "IDLE (Bidirectional)"
                    elif raw_tx_mode == "1":
                        tx_string = "ARMED (Bidirectional)"
                    elif raw_tx_mode == "2":
                        tx_string = "POWERED ASCENT (Unidirectional)"
                    elif raw_tx_mode == "3":
                        tx_string = "COASTING (Unidirectional)"
                    elif raw_tx_mode == "4":
                        tx_string = "DESCENT (Unidirectional)"
                    elif raw_tx_mode == "5":
                        tx_string = "RECOVERY (Unidirectional)"
                    else:
                        tx_string = f"UNKNOWN ({raw_tx_mode})"

                    if raw_rx_mode == "0":
                        rx_string = "BIDIRECTIONAL"
                    elif raw_rx_mode == "1":
                        rx_string = "UNIDIRECTIONAL"
                    else:
                        rx_string = f"UNKNOWN ({raw_rx_mode})"
                        
                    rssi, snr = int(parts[16]), float(parts[17])

                    config.data_history["time"].append(current_timestamp)
                    config.data_history["pos_x"].append(x_pos)
                    config.data_history["pos_y"].append(y_pos)
                    config.data_history["pos_z"].append(z_pos)
                    config.data_history["vel_x"].append(x_vel)
                    config.data_history["vel_y"].append(y_vel)
                    config.data_history["vel_z"].append(z_vel)
                    config.data_history["acc_x"].append(x_acc)
                    config.data_history["acc_y"].append(y_acc)
                    config.data_history["acc_z"].append(z_acc)
                    config.data_history["pitch"].append(pitch)
                    config.data_history["roll"].append(roll)
                    config.data_history["yaw"].append(yaw)
                    config.data_history["alt"].append(alt)
                    config.data_history["temp"].append(temp)

                    config.status_data["tx_mode"] = tx_string
                    config.status_data["rx_mode"] = rx_string
                    config.status_data["raw_tx_mode"] = raw_tx_mode
                    config.status_data["rssi"] = rssi
                    config.status_data["snr"] = snr

                    for idx, key in enumerate(["pos_x","pos_y","pos_z","vel_x","vel_y","vel_z","acc_x","acc_y","acc_z","pitch","roll","yaw","alt","temp"]):
                        config.bottom_row_data[key] = parts[idx]
                    
                    config.bottom_row_data["tx_mode"] = tx_string
                    config.bottom_row_data["rx_mode"] = rx_string
                    config.bottom_row_data["rssi"] = parts[16]
                    config.bottom_row_data["snr"] = parts[17]

                    while config.data_history["time"] and (current_timestamp - config.data_history["time"][0] > config.MAX_HISTORY_SEC):
                        for key in config.data_history:
                            config.data_history[key].pop(0)
        except Exception:
            pass