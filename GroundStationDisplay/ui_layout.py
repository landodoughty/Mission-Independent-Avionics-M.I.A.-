# ui_layout.py
import dearpygui.dearpygui as dpg
import serial.tools.list_ports
import ui_callbacks

def setup_themes():
    with dpg.theme() as red_theme:
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_Button, [180, 50, 50])
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, [220, 60, 60])
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, [140, 40, 40])

    with dpg.theme() as yellow_theme:
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_Button, [200, 140, 20])
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, [240, 170, 30])
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, [160, 110, 15])

    with dpg.theme() as grey_theme:
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_Button, [70, 70, 70])
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, [70, 70, 70])
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, [70, 70, 70])
            dpg.add_theme_color(dpg.mvThemeCol_Text, [130, 130, 130])
            
    return red_theme, yellow_theme, grey_theme

def build_gui_layout(red_theme, yellow_theme):
    with dpg.window(tag="main_window", label="Pico Telemetry Command Center", no_close=True, no_move=True, no_resize=True):
        
        # --- CONTROL DECK TOP BLOCK ---
        with dpg.group(horizontal=True):
            with dpg.child_window(width=460, height=105, label="Commands"):
                dpg.add_text("Command Uplink:")
                with dpg.group(horizontal=True):
                    with dpg.group():
                        with dpg.group(horizontal=True):
                            dpg.add_input_text(tag="cmd_input", hint="Type command...", width=130, on_enter=True, callback=ui_callbacks.trigger_manual_send_cb)
                            dpg.add_button(label="Send", width=45, callback=ui_callbacks.trigger_manual_send_cb)
                    
                    dpg.add_spacer(width=10)
                    with dpg.group():
                        with dpg.group(horizontal=True):
                            safety_btn = dpg.add_button(label="ARM", tag="btn_safety_action", width=115, height=24, callback=ui_callbacks.trigger_safety_action_cb)
                            dpg.bind_item_theme(safety_btn, yellow_theme)
                            
                            critical_btn = dpg.add_button(label="LAUNCH", tag="btn_critical_action", width=115, height=24, callback=ui_callbacks.trigger_critical_action_cb)
                        dpg.add_checkbox(label="Purge on Launch", default_value=False, tag="chk_purge_on_launch")
            
            with dpg.child_window(width=540, height=105, label="Configuration & Interface"):
                with dpg.group(horizontal=True):
                    dpg.add_text("Dashboard View:")
                    dpg.add_text(" [STREAM PAUSED]", tag="txt_pause_indicator", color=[255, 50, 50], show=False)
                    dpg.add_spacer(width=40)
                    dpg.add_text("Port: UNINITIALIZED", tag="txt_active_port", color=[255, 200, 0])
                
                with dpg.group(horizontal=True):
                    with dpg.group():
                        with dpg.group(horizontal=True):
                            dpg.add_combo(
                                items=["Show All Data", "5 seconds", "10 seconds", "15 seconds", "30 seconds", "60 seconds"],
                                default_value="Show All Data", width=120, callback=ui_callbacks.dropdown_filter_cb
                            )
                            reset_btn = dpg.add_button(label="Reset", width=45, callback=ui_callbacks.reset_data_cb)
                            dpg.bind_item_theme(reset_btn, red_theme)
                        
                        with dpg.group(horizontal=True):
                            dpg.add_button(label="Pause Stream", tag="btn_pause_stream", width=95, callback=ui_callbacks.toggle_stream_pause_cb)
                            dpg.add_button(label="Save Flight", width=95, callback=ui_callbacks.export_flight_csv_cb)
                    
                    dpg.add_spacer(width=25)
                    dpg.add_button(label="Change Port", width=100, height=35, callback=ui_callbacks.open_change_port_modal_cb)
            
            with dpg.child_window(width=-1, height=105, label="Status"):
                with dpg.group(horizontal=True):
                    with dpg.group():
                        dpg.add_text("Flight Computer(TX) Mode: UNKNOWN", tag="txt_tx_mode", color=[0, 255, 0])
                        dpg.add_text("Ground Station(RX) Mode: UNKNOWN", tag="txt_rx_mode", color=[180, 255, 100])
                    
                    dpg.add_spacer(width=40)
                    with dpg.group():
                        dpg.add_text("RSSI: 0 dBm", tag="txt_rssi", color=[0, 200, 255])
                        dpg.add_text("SNR: 0 dB", tag="txt_snr", color=[255, 200, 0])

        dpg.add_separator()

        # --- CORE RESPONSIVE GRAPH MATRIX GRID LAYER ---
        with dpg.subplots(2, 2, row_ratios=[1, 1], column_ratios=[1, 1], width=-1, height=-110):
            with dpg.plot(label="Live Position Profile"):
                dpg.add_plot_legend()
                dpg.add_plot_axis(dpg.mvXAxis, label="Elapsed Connection Time (Seconds)", tag="x_axis_pos")
                with dpg.plot_axis(dpg.mvYAxis, label="Position (m)", tag="y_axis_pos"):
                    dpg.add_line_series([], [], label="X Pos", tag="series_pos_x")
                    dpg.add_line_series([], [], label="Y Pos", tag="series_pos_y")
                    dpg.add_line_series([], [], label="Z Pos", tag="series_pos_z")

            with dpg.plot(label="Linear Acceleration"):
                dpg.add_plot_legend()
                dpg.add_plot_axis(dpg.mvXAxis, label="Elapsed Connection Time (Seconds)", tag="x_axis_acc")
                with dpg.plot_axis(dpg.mvYAxis, label="Acc (m/s²)", tag="y_axis_acc"):
                    dpg.add_line_series([], [], label="X Acc", tag="series_acc_x")
                    dpg.add_line_series([], [], label="Y Acc", tag="series_acc_y")
                    dpg.add_line_series([], [], label="Z Acc", tag="series_acc_z")

            with dpg.plot(label="Attitude Angles"):
                dpg.add_plot_legend()
                dpg.add_plot_axis(dpg.mvXAxis, label="Elapsed Connection Time (Seconds)", tag="x_axis_ori")
                with dpg.plot_axis(dpg.mvYAxis, label="Degrees (°)", tag="y_axis_ori"):
                    dpg.add_line_series([], [], label="Pitch", tag="series_ori_p")
                    dpg.add_line_series([], [], label="Roll", tag="series_ori_r")
                    dpg.add_line_series([], [], label="Yaw", tag="series_ori_y")

            with dpg.plot(label="Altitude Profile"):
                dpg.add_plot_legend()
                dpg.add_plot_axis(dpg.mvXAxis, label="Elapsed Connection Time (Seconds)", tag="x_axis_alt")
                with dpg.plot_axis(dpg.mvYAxis, label="Altitude (m)", tag="y_axis_alt"):
                    dpg.add_line_series([], [], label="Altitude", tag="series_alt")

        dpg.add_separator()

        # --- LOWER HORIZONTAL ROW PANEL (Responsive Telemetry Row Inspector) ---
        with dpg.child_window(width=-1, height=-1, label="Live Inspector Row"):
            dpg.add_text("LATEST TELEMETRY PACKET STREAM INSPECTOR", color=[255, 200, 0])
            with dpg.group(horizontal=True):
                with dpg.group():
                    with dpg.group(horizontal=True):
                        dpg.add_text("X Pos:", color=[160, 160, 160])
                        dpg.add_text("0.00", tag="btm_pos_x", color=[0, 255, 255])
                    with dpg.group(horizontal=True):
                        dpg.add_text("Y Pos:", color=[160, 160, 160])
                        dpg.add_text("0.00", tag="btm_pos_y", color=[0, 255, 255])
                    with dpg.group(horizontal=True):
                        dpg.add_text("Z Pos:", color=[160, 160, 160])
                        dpg.add_text("0.00", tag="btm_pos_z", color=[0, 255, 255])
                
                dpg.add_spacer(width=30)
                with dpg.group():
                    with dpg.group(horizontal=True):
                        dpg.add_text("X Vel:", color=[160, 160, 160])
                        dpg.add_text("0.00", tag="btm_vel_x", color=[0, 255, 255])
                    with dpg.group(horizontal=True):
                        dpg.add_text("Y Vel:", color=[160, 160, 160])
                        dpg.add_text("0.00", tag="btm_vel_y", color=[0, 255, 255])
                    with dpg.group(horizontal=True):
                        dpg.add_text("Z Vel:", color=[160, 160, 160])
                        dpg.add_text("0.00", tag="btm_vel_z", color=[0, 255, 255])

                dpg.add_spacer(width=30)
                with dpg.group():
                    with dpg.group(horizontal=True):
                        dpg.add_text("X Acc:", color=[160, 160, 160])
                        dpg.add_text("0.00", tag="btm_acc_x", color=[0, 255, 255])
                    with dpg.group(horizontal=True):
                        dpg.add_text("Y Acc:", color=[160, 160, 160])
                        dpg.add_text("0.00", tag="btm_acc_y", color=[0, 255, 255])
                    with dpg.group(horizontal=True):
                        dpg.add_text("Z Acc:", color=[160, 160, 160])
                        dpg.add_text("0.00", tag="btm_acc_z", color=[0, 255, 255])

                dpg.add_spacer(width=30)
                with dpg.group():
                    with dpg.group(horizontal=True):
                        dpg.add_text("Pitch:", color=[160, 160, 160])
                        dpg.add_text("0.00", tag="btm_pitch", color=[0, 255, 255])
                    with dpg.group(horizontal=True):
                        dpg.add_text("Roll: ", color=[160, 160, 160])
                        dpg.add_text("0.00", tag="btm_roll", color=[0, 255, 255])
                    with dpg.group(horizontal=True):
                        dpg.add_text("Yaw:  ", color=[160, 160, 160])
                        dpg.add_text("0.00", tag="btm_yaw", color=[0, 255, 255])

                dpg.add_spacer(width=30)
                with dpg.group():
                    with dpg.group(horizontal=True):
                        dpg.add_text("Altitude:   ", color=[160, 160, 160])
                        dpg.add_text("0.00 m", tag="btm_alt", color=[255, 200, 0])
                    with dpg.group(horizontal=True):
                        dpg.add_text("Temperature:", color=[160, 160, 160])
                        dpg.add_text("0.00 C", tag="btm_temp", color=[255, 200, 0])
                
                dpg.add_spacer(width=30)
                with dpg.group():
                    with dpg.group(horizontal=True):
                        dpg.add_text("FC (TX) Mode:", color=[160, 160, 160])
                        dpg.add_text("UNKNOWN", tag="btm_tx_mode", color=[0, 255, 0])
                    with dpg.group(horizontal=True):
                        dpg.add_text("GS (RX) Mode:", color=[160, 160, 160])
                        dpg.add_text("UNKNOWN", tag="btm_rx_mode", color=[180, 255, 100])
                
                dpg.add_spacer(width=30)
                with dpg.group():
                    with dpg.group(horizontal=True):
                        dpg.add_text("RSSI:", color=[160, 160, 160])
                        dpg.add_text("0 dBm", tag="btm_rssi", color=[0, 200, 255])
                    with dpg.group(horizontal=True):
                        dpg.add_text("SNR: ", color=[160, 160, 160])
                        dpg.add_text("0.0 dB", tag="btm_snr", color=[255, 200, 0])

def build_modals(red_theme):
    with dpg.window(label="Safety Execution Confirmation", modal=True, tag="confirm_modal", show=False, width=380, height=140, pos=(480, 320), no_close=True, no_resize=True):
        dpg.add_text("Are you sure you want to execute this command?", color=[255, 200, 0])
        dpg.add_spacer(height=3)
        dpg.add_text("Payload: ''", tag="txt_confirm_payload", color=[0, 255, 255])
        dpg.add_spacer(height=8)
        with dpg.group(horizontal=True):
            confirm_btn = dpg.add_button(label="Confirm & Send", width=140, callback=ui_callbacks.confirm_execution_cb)
            dpg.bind_item_theme(confirm_btn, red_theme)
            dpg.add_button(label="Cancel", width=100, callback=ui_callbacks.cancel_execution_cb)

    initial_ports = [p.device for p in serial.tools.list_ports.comports()]
    if not initial_ports:
        initial_ports = ["No COM Ports Detected"]

    with dpg.window(label="Hardware Interface Configuration", modal=True, tag="port_select_modal", width=420, height=160, pos=(460, 300), no_close=True, no_resize=True):
        dpg.add_text("Select Hardware Interface Connection:", color=[255, 200, 0])
        dpg.add_spacer(height=5)
        dpg.add_combo(items=initial_ports, default_value=initial_ports[0], tag="com_dropdown", width=380)
        dpg.add_spacer(height=8)
        with dpg.group(horizontal=True):
            dpg.add_button(label="Connect Target", width=140, callback=ui_callbacks.connect_port_cb)
            dpg.add_button(label="Rescan Buses", width=120, callback=ui_callbacks.rescan_ports_cb)
        dpg.add_spacer(height=5)
        dpg.add_text("", tag="popup_error_msg", color=[255, 50, 50])