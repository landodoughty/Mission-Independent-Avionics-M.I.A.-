# main.py
import threading
import dearpygui.dearpygui as dpg
import config
import serial_worker
import ui_callbacks
import ui_layout

def update_gui_frame(red_theme, grey_theme):
    if not dpg.is_dearpygui_running():
        return

    # Update Text Labels
    dpg.set_value("txt_tx_mode", f"Flight Computer(TX) Mode: {config.status_data['tx_mode']}")
    dpg.set_value("txt_rx_mode", f"Ground Station(RX) Mode: {config.status_data['rx_mode']}")
    dpg.set_value("txt_rssi", f"RSSI: {config.status_data['rssi']} dBm")
    dpg.set_value("txt_snr",  f"SNR: {config.status_data['snr']} dB")

    # 1. Update Arm/Disarm Safety Button State
    if config.status_data["raw_tx_mode"] == "1":
        dpg.configure_item("btn_safety_action", label="DISARM")
    else:
        dpg.configure_item("btn_safety_action", label="ARM")

    # 2. Dynamic Interlocks for Launch/Reset Actions
    if "Unidirectional" in config.status_data["tx_mode"] or config.status_data["rx_mode"] == "UNIDIRECTIONAL":
        dpg.configure_item("btn_critical_action", label="RESET", enabled=True)
        dpg.configure_item("chk_purge_on_launch", label="Purge on Reset")
        dpg.bind_item_theme("btn_critical_action", red_theme)
    else:
        dpg.configure_item("chk_purge_on_launch", label="Purge on Launch")
        
        if config.status_data["raw_tx_mode"] == "1":
            dpg.configure_item("btn_critical_action", label="LAUNCH", enabled=True)
            dpg.bind_item_theme("btn_critical_action", red_theme)
        else:
            dpg.configure_item("btn_critical_action", label="LAUNCH", enabled=False)
            dpg.bind_item_theme("btn_critical_action", grey_theme)

    for key, val in config.bottom_row_data.items():
        dpg.set_value(f"btm_{key}", f"{val}")

    if not config.data_history["time"]:
        return

    times = config.data_history["time"]
    latest_time = times[-1]

    if config.selected_window == 0.0:
        slice_idx = 0
    else:
        cutoff = latest_time - config.selected_window
        slice_idx = 0
        for i, t in enumerate(times):
            if t >= cutoff:
                slice_idx = i
                break

    t_slice = times[slice_idx:]
    min_t = t_slice[0]
    max_t = t_slice[-1]

    # Update plots
    dpg.set_value("series_pos_x", [t_slice, config.data_history["pos_x"][slice_idx:]])
    dpg.set_value("series_pos_y", [t_slice, config.data_history["pos_y"][slice_idx:]])
    dpg.set_value("series_pos_z", [t_slice, config.data_history["pos_z"][slice_idx:]])

    dpg.set_value("series_acc_x", [t_slice, config.data_history["acc_x"][slice_idx:]])
    dpg.set_value("series_acc_y", [t_slice, config.data_history["acc_y"][slice_idx:]])
    dpg.set_value("series_acc_z", [t_slice, config.data_history["acc_z"][slice_idx:]])

    dpg.set_value("series_ori_p", [t_slice, config.data_history["pitch"][slice_idx:]])
    dpg.set_value("series_ori_r", [t_slice, config.data_history["roll"][slice_idx:]])
    dpg.set_value("series_ori_y", [t_slice, config.data_history["yaw"][slice_idx:]])

    dpg.set_value("series_alt",   [t_slice, config.data_history["alt"][slice_idx:]])

    x_axis_title = "Time Relative to T-0 Event (Seconds)" if config.launch_time is not None else "Elapsed Connection Time (Seconds)"
    for x_axis in ["x_axis_pos", "x_axis_acc", "x_axis_ori", "x_axis_alt"]:
        dpg.set_axis_limits(x_axis, min_t, max_t)
        dpg.configure_item(x_axis, label=x_axis_title)

    ui_callbacks.apply_padded_autoscale("y_axis_pos", ["pos_x", "pos_y", "pos_z"], slice_idx)
    ui_callbacks.apply_padded_autoscale("y_axis_acc", ["acc_x", "acc_y", "acc_z"], slice_idx)
    ui_callbacks.apply_padded_autoscale("y_axis_ori", ["pitch", "roll", "yaw"], slice_idx)
    ui_callbacks.apply_padded_autoscale("y_axis_alt", ["alt"], slice_idx)

def main():
    dpg.create_context()
    
    # Load and register style colors
    red_theme, yellow_theme, grey_theme = ui_layout.setup_themes()
    
    # Generate View Windows and Dialog Modals
    ui_layout.build_gui_layout(red_theme, yellow_theme)
    ui_layout.build_modals(red_theme)
    
    # Fire up background hardware worker parsing loop
    threading.Thread(target=serial_worker.serial_read_thread, daemon=True).start()
    
    # Initialize Core Window Viewport
    dpg.create_viewport(title='Custom Pico Telemetry Control Panel', width=1350, height=850)
    dpg.set_viewport_resize_callback(ui_callbacks.resize_viewport_cb)
    
    dpg.setup_dearpygui()
    dpg.show_viewport()
    
    # Maximize natively with standard window borders intact
    dpg.maximize_viewport()
    ui_callbacks.resize_viewport_cb()
    
    # Master Application Context State Machine Loop
    while dpg.is_dearpygui_running():
        update_gui_frame(red_theme, grey_theme)
        dpg.render_dearpygui_frame()
        
    dpg.destroy_context()
    
    # Resource Cleanup Closure
    if config.ser and config.ser.is_open:
        config.ser.close()

if __name__ == "__main__":
    main()