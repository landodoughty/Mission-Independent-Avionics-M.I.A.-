# config.py
import time

# --- CONSTANTS ---
BAUD_RATE = 115200
MAX_HISTORY_SEC = 60  

# --- SERIAL CONNECTION POINTERS ---
SERIAL_PORT = None  
ser = None
staged_command = ""  
is_stream_paused = False  

# --- TIMELINE ANCHORS ---
start_time = time.time()
launch_time = None      
selected_window = 0.0  

# --- TELEMETRY STORAGE MATRICES ---
data_history = {
    "time": [],
    "pos_x": [], "pos_y": [], "pos_z": [],
    "vel_x": [], "vel_y": [], "vel_z": [],
    "acc_x": [], "acc_y": [], "acc_z": [],
    "pitch": [], "roll":  [], "yaw":   [],
    "alt":   [], "temp":  []
}

status_data = {
    "tx_mode": "UNKNOWN", 
    "rx_mode": "UNKNOWN", 
    "raw_tx_mode": "0",
    "rssi": 0, 
    "snr": 0
}

bottom_row_data = {k: "0.00" for k in data_history.keys() if k != "time"}
bottom_row_data.update({"tx_mode": "UNKNOWN", "rx_mode": "UNKNOWN", "rssi": "0", "snr": "0.0"})