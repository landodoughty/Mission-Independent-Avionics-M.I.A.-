# ui_callbacks.py
import time
import csv
import serial
import serial.tools.list_ports
import dearpygui.dearpygui as dpg
import tkinter as tk
from tkinter import filedialog
import config

def connect_port_cb():
    selected_port = dpg.get_value("com_dropdown")
    if not selected_port or selected_port == "No COM Ports Detected":
        dpg.set_value("popup_error_msg", "Please select a valid target channel.")
        return
        
    config.SERIAL_PORT = selected_port.split(" ")[0]
    
    try:
        config.ser = serial.Serial(config.SERIAL_PORT, config.BAUD_RATE, timeout=0.1)
        print(f"Successfully attached to serial channel: {config.SERIAL_PORT}")
        config.start_time = time.time()
        
        dpg.set_value("txt_active_port", f"Port: {config.SERIAL_PORT}")
        dpg.configure_item("port_select_modal", show=False)
    except Exception as e:
        dpg.set_value("popup_error_msg", f"Connection Failed: {e}")

def open_change_port_modal_cb():
    if config.ser and config.ser.is_open:
        config.ser.close()
    config.ser = None
    dpg.set_value("txt_active_port", "Port: DISCONNECTED")
    rescan_ports_cb()
    dpg.configure_item("port_select_modal", show=True)

def rescan_ports_cb():
    ports = [p.device for p in serial.tools.list_ports.comports()]
    if not ports:
        ports = ["No COM Ports Detected"]
    dpg.configure_item("com_dropdown", items=ports, default_value=ports[0])
    dpg.set_value("popup_error_msg", "")

def trigger_manual_send_cb():
    cmd = dpg.get_value("cmd_input")
    if not cmd:
        return
    config.staged_command = cmd
    dpg.set_value("txt_confirm_payload", f"Payload: '{config.staged_command}'")
    dpg.configure_item("confirm_modal", show=True)

def trigger_safety_action_cb():
    if config.status_data["raw_tx_mode"] == "1":
        config.staged_command = "disarm"
        dpg.set_value("txt_confirm_payload", "Payload: 'disarm' [SAFETY INTERLOCK]")
    else:
        config.staged_command = "arm"
        dpg.set_value("txt_confirm_payload", "Payload: 'arm' [SAFETY INTERLOCK]")
    dpg.configure_item("confirm_modal", show=True)

def trigger_critical_action_cb():
    if "Unidirectional" in config.status_data["tx_mode"] or config.status_data["rx_mode"] == "UNIDIRECTIONAL":
        config.staged_command = "reset"
        dpg.set_value("txt_confirm_payload", "Payload: 'reset' [HARDWARE OVERRIDE]")
    else:
        config.staged_command = "launch"
        dpg.set_value("txt_confirm_payload", "Payload: 'launch' [CRITICAL EVENT]")
        
    dpg.configure_item("confirm_modal", show=True)

def confirm_execution_cb():
    if config.ser and config.ser.is_open and config.staged_command:
        if config.staged_command.strip().lower() == "launch":
            now_unix = time.time()
            config.launch_time = now_unix
            
            should_purge = dpg.get_value("chk_purge_on_launch")
            
            if should_purge:
                for key in config.data_history:
                    config.data_history[key].clear()
                print("Launch confirmed: Purging historical telemetry buffers.")
            else:
                time_delta = now_unix - config.start_time
                config.data_history["time"] = [t - time_delta for t in config.data_history["time"]]
                print("Launch confirmed: Shifting historical timelines relative to T-0.")

        config.ser.write((config.staged_command + '\n').encode('utf-8'))
        print(f"Uplink package transmitted: {config.staged_command}")
        if config.staged_command not in ["launch", "reset", "arm", "disarm"]:
            dpg.set_value("cmd_input", "")
            
    config.staged_command = ""
    dpg.configure_item("confirm_modal", show=False)

def cancel_execution_cb():
    config.staged_command = ""
    dpg.configure_item("confirm_modal", show=False)

def reset_data_cb():
    config.start_time = time.time()
    config.launch_time = None
    for key in config.data_history:
        config.data_history[key].clear()
    for key in config.bottom_row_data:
        config.bottom_row_data[key] = "0.00" if key not in ["tx_mode", "rx_mode", "rssi", "snr"] else "UNKNOWN"
    print("Dashboard telemetry arrays and master timeline anchors successfully flushed.")

def toggle_stream_pause_cb():
    config.is_stream_paused = not config.is_stream_paused
    if config.is_stream_paused:
        dpg.configure_item("btn_pause_stream", label="Resume Stream")
        dpg.configure_item("txt_pause_indicator", show=True)
    else:
        dpg.configure_item("btn_pause_stream", label="Pause Stream")
        dpg.configure_item("txt_pause_indicator", show=False)

def export_flight_csv_cb():
    if not config.data_history["time"]:
        print("Export Aborted: Telemetry data matrix is empty.")
        return
    
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    
    selected_path = filedialog.asksaveasfilename(
        title="Select Target Export Destination Profile",
        initialfile=f"flight_telemetry_dump_{int(time.time())}.csv",
        defaultextension=".csv",
        filetypes=[("Comma Separated Sheets", "*.csv"), ("All System Profiles", "*.*")]
    )
    root.destroy()
    
    if not selected_path:
        print("Export Aborted: No target path directory selected.")
        return

    try:
        with open(selected_path, mode='w', newline='') as csv_file:
            writer = csv.writer(csv_file)
            headers = ["Relative_Time_Sec", "Pos_X", "Pos_Y", "Pos_Z", "Vel_X", "Vel_Y", "Vel_Z", "Acc_X", "Acc_Y", "Acc_Z", "Pitch", "Roll", "Yaw", "Altitude", "Temperature"]
            writer.writerow(headers)
            
            for i in range(len(config.data_history["time"])):
                row = [
                    config.data_history["time"][i],      config.data_history["pos_x"][i], config.data_history["pos_y"][i], config.data_history["pos_z"][i],
                    config.data_history["vel_x"][i],     config.data_history["vel_y"][i], config.data_history["vel_z"][i], config.data_history["acc_x"][i],
                    config.data_history["acc_y"][i],     config.data_history["acc_z"][i], config.data_history["pitch"][i], config.data_history["roll"][i],
                    config.data_history["yaw"][i],       config.data_history["alt"][i],   config.data_history["temp"][i]
                ]
                writer.writerow(row)
        print(f"Flight telemetry package successfully exported: '{selected_path}'")
    except Exception as e:
        print(f"Error compiling output flight sheet payload: {e}")

def dropdown_filter_cb(sender, app_data):
    if app_data == "Show All Data":
        config.selected_window = 0.0
    else:
        config.selected_window = float(app_data.split()[0])

def apply_padded_autoscale(axis_id, dataset_keys, slice_idx):
    all_values = []
    for key in dataset_keys:
        all_values.extend(config.data_history[key][slice_idx:])
    
    if not all_values:
        dpg.set_axis_limits(axis_id, 0.0, 1.0)
        return

    data_min = min(all_values)
    data_max = max(all_values)
    data_range = data_max - data_min

    if data_range == 0:
        padding = 1.0 if data_min == 0 else abs(data_min) * 0.1
    else:
        padding = data_range * 0.1

    dpg.set_axis_limits(axis_id, data_min - padding, data_max + padding)

def resize_viewport_cb():
    vp_width = dpg.get_viewport_width()
    vp_height = dpg.get_viewport_height()
    dpg.configure_item("main_window", width=vp_width - 16, height=vp_height - 38)