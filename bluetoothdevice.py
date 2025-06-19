

import dbus
import dbus.service
import dbus.mainloop.glib
import os
import subprocess
import time
from gi.repository import GObject
import mimetypes
from dbus.mainloop.glib import DBusGMainLoop



dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

class BluetoothDeviceManager:
    def __init__(self):
        self.bus = dbus.SystemBus()
        self.adapter_path = '/org/bluez/hci0'
        self.adapter_proxy = self.bus.get_object('org.bluez', self.adapter_path)
        self.adapter = dbus.Interface(self.adapter_proxy, 'org.bluez.Adapter1')
        self.adapter_proxy = self.bus.get_object('org.bluez',self.adapter_path)
        self.adapter = dbus.Interface(self.adapter_proxy, 'org.bluez.Adapter1')
        self.stream_process = None
        self.device_path = None
        self.device_address = None
        self.device_sink = None
        self.devices = {}
        self.last_session_path = None
        self.opp_process = None

    def start_discovery(self):
        """Function to start discovery"""
        self.adapter.StartDiscovery()

    def stop_discovery(self):
        """Function to stop discovery"""
        self.adapter.StopDiscovery()

    def inquiry(self,timeout):
        """Function for inquiry with inquiry timeout being mentioned"""
        self.start_discovery()
        time.sleep(timeout)
        self.stop_discovery()
        devices = []
        bus = dbus.SystemBus()
        om = dbus.Interface(bus.get_object("org.bluez", "/"), "org.freedesktop.DBus.ObjectManager")
        objects = om.GetManagedObjects()
        for path, interfaces in objects.items():
            if "org.bluez.Device1" in interfaces:
                devices.append(path)
        for device_path in devices:
            device = dbus.Interface(bus.get_object("org.bluez", device_path), dbus_interface="org.bluez.Device1")
            device_props = dbus.Interface(bus.get_object("org.bluez", device_path),dbus_interface="org.freedesktop.DBus.Properties")
            device_address = device_props.Get("org.bluez.Device1", "Address")
            print("Device Address")
            print(device_address)
            print("Device Name")
            device_name = device_props.Get("org.bluez.Device1", "Alias")
            print(device_name)

    # def pair(self, address):
    #     """Function for pairing of the device"""
    #     device_path = self.find_device_path(address)
    #     if device_path:
    #         try:
    #             device = dbus.Interface(self.bus.get_object("org.bluez", device_path),dbus_interface="org.bluez.Device1")
    #             device.Pair()
    #             # Check if paired
    #             props = dbus.Interface(self.bus.get_object("org.bluez", device_path), "org.freedesktop.DBus.Properties")
    #             paired = props.Get("org.bluez.Device1", "Paired")
    #             if paired:
    #                 print("Pairing is successful")
    #                 return True
    #             else:
    #                 print("Pairing attempted but not confirmed")
    #                 return False
    #         except Exception as e:
    #             print(f"Pairing failed: {e}")
    #             return False
    #     else:
    #         print("Device path not found for pairing")
    #         return False


    def pair(self, address):
        """Function for pairing of the device"""

        device_path = self.find_device_path(address)
        if device_path:
            try:
                device = dbus.Interface(
                    self.bus.get_object("org.bluez", device_path),
                    dbus_interface="org.bluez.Device1"
                )
                print(f"Initiating pairing with {device_path}")
                device.Pair()

                # Wait up to 10 seconds for the user to confirm and BlueZ to mark as paired
                props = dbus.Interface(
                    self.bus.get_object("org.bluez", device_path),
                    "org.freedesktop.DBus.Properties"
                )

                import time
                for _ in range(20):  # 20 * 0.5s = 10 seconds max
                    paired = props.Get("org.bluez.Device1", "Paired")
                    if paired:
                        print("Pairing is successful")
                        return True
                    time.sleep(20)

                print("Pairing attempted but not confirmed")
                return False

            except dbus.exceptions.DBusException as e:
                print(f"Pairing failed: {e.get_dbus_message()}")
                return False
            except Exception as e:
                print(f"Unexpected error during pairing: {e}")
                return False
        else:
            print("Device path not found for pairing")
            return False

    # def pair(self, address):
    #     device_path = self.find_device_path(address)
    #     if not device_path:
    #         print("Device not found.")
    #         return False
    #
    #     if self.confirmation_callback:
    #         self.agent_runner.confirmation_requested.connect(self.confirmation_callback)
    #
    #     try:
    #         device = dbus.Interface(
    #             self.bus.get_object("org.bluez", device_path),
    #             "org.bluez.Device1"
    #         )
    #         print(f"[BluetoothDeviceManager] Initiating pairing with {device_path}")
    #         device.Pair()
    #
    #         props = dbus.Interface(
    #             self.bus.get_object("org.bluez", device_path),
    #             "org.freedesktop.DBus.Properties"
    #         )
    #         for _ in range(20):
    #             if props.Get("org.bluez.Device1", "Paired"):
    #                 print("Pairing successful.")
    #                 return True
    #             time.sleep(0.5)
    #         print("Pairing attempted but not confirmed.")
    #         return False
    #
    #     except dbus.exceptions.DBusException as e:
    #         print(f"Pairing failed: {e.get_dbus_message()}")
    #         return False



    def br_edr_connect(self, address):
        """Function for BR/EDR connection"""
        device_path = self.find_device_path(address)
        if device_path:
            try:
                device = dbus.Interface(self.bus.get_object("org.bluez", device_path),dbus_interface="org.bluez.Device1")
                device.Connect()
                # Check if connected
                props = dbus.Interface(self.bus.get_object("org.bluez", device_path), "org.freedesktop.DBus.Properties")
                connected = props.Get("org.bluez.Device1", "Connected")
                if connected:
                    print("Connection is successful")
                    return True
                else:
                    print("Connection attempted but not confirmed")
                    return False
            except Exception as e:
                print(f"Connection failed: {e}")
                return False
        else:
            print("Device path not found for connection")
            return False

    def le_connect(self, address):
        """Function for LE connection"""
        device_path = self.find_device_path(address)
        if device_path:
            try:
                device = dbus.Interface(self.bus.get_object("org.bluez", device_path),dbus_interface="org.bluez.Device1")
                device.ConnectProfile('0000110e-0000-1000-8000-00805f9b34fb')  # HID profile
            except Exception as e:
                print("LE Connection has failed")

    def set_discoverable_on(self):
        """Sets the Bluetooth device to be discoverable."""
        print("Setting Bluetooth device to be discoverable...")
        command = "hciconfig hci0 piscan"
        subprocess.run(command, shell = True)
        print("Bluetooth device is now discoverable.")

    def set_discoverable_off(self):
        """Sets the Bluetooth device to be non-discoverable."""
        print("Setting Bluetooth device to be non-discoverable...")
        command = "hciconfig hci0 noscan"
        subprocess.run(command, shell = True)
        print("Bluetooth device is now non-discoverable.")

    def is_device_paired(self, device_address):
        "Function to check whether the device is paired "
        device_path = self.find_device_path(device_address)
        if not device_path:
            return False
        bus = dbus.SystemBus()
        props = dbus.Interface(bus.get_object("org.bluez", device_path),"org.freedesktop.DBus.Properties")
        try:
            return props.Get("org.bluez.Device1", "Paired")
        except dbus.exceptions.DBusException:
            return False

    def is_device_connected(self, device_address):
        "Function to check whether the device is connected or not"
        device_path = self.find_device_path(device_address)
        if not device_path:
            return False
        bus = dbus.SystemBus()
        props = dbus.Interface(bus.get_object("org.bluez", device_path),"org.freedesktop.DBus.Properties")
        try:
            return props.Get("org.bluez.Device1", "Connected")
        except dbus.exceptions.DBusException:
            return False

    def set_device_address(self, address):
        """Set the current device for streaming and media control."""
        self.device_address = address
        self.device_path = self.find_device_path(address)
        self.device_sink = self.get_sink_for_device(address)


    def _get_device_path(self):
        if not self.device_address:
            raise Exception("Device address not set")
        formatted_address = self.device_address.replace(":", "_")
        return f"/org/bluez/hci0/dev_{formatted_address}"


    def find_device_path(self, address):
        """Find the device path by Bluetooth address."""
        # This function assumes you're using Bluez
        om = dbus.Interface(self.bus.get_object("org.bluez", "/"), "org.freedesktop.DBus.ObjectManager")
        objects = om.GetManagedObjects()
        for path, interfaces in objects.items():
            if "org.bluez.Device1" in interfaces:
                props = interfaces["org.bluez.Device1"]
                if props.get("Address") == address:
                    return path
        return None

    def get_sink_for_device(self, address):
        """Get the PulseAudio sink for the Bluetooth device."""
        try:
            sinks_output = subprocess.check_output(["pactl", "list", "short", "sinks"], text=True)
            address_formatted = address.replace(":", "_").lower()
            for line in sinks_output.splitlines():
                if address_formatted in line.lower():
                    sink_name = line.split()[1]
                    return sink_name
        except Exception as e:
            print(f"Error getting sink for device: {e}")
        return None


    def start_streaming(self, device_address, audio_file):
        """Start A2DP streaming with the provided audio file path."""
        print(f"Starting A2DP streaming to {device_address} with file: {audio_file}")

        # Check if the device address corresponds to a valid device
        device_path = self.find_device_path(device_address)
        if not device_path:
            print(f"Device path not found for address {device_address}")
            return False

        # Get the PulseAudio sink for this device (make sure the correct sink is set)
        self.device_sink = self.get_sink_for_device(device_address)
        if not self.device_sink:
            print("No PulseAudio sink found for the selected Bluetooth device.")
            return False

        try:
            # Run aplay and redirect to the selected Bluetooth sink
            self.stream_process = subprocess.Popen(
                ["aplay", "-D", "pulse", audio_file],
                env={**subprocess.os.environ, "PULSE_SINK": self.device_sink}
            )
            print(f"Streaming audio to {device_address}")
            return True
        except Exception as e:
            print(f"Error while starting streaming: {e}")
            return False

    def stop_streaming(self):
        """Stop the A2DP streaming process."""
        print("Stopping A2DP streaming...")
        if self.stream_process:
            try:
                self.stream_process.terminate()
                self.stream_process.wait()
                self.stream_process = None
                print("Streaming stopped successfully.")
                return True
            except Exception as e:
                print(f"Error while stopping streaming: {e}")
                return False
        else:
            print("No active streaming process.")
            return False


    def _get_media_control_interface(self, address):
        """Finds the MediaControl1 interface associated with a specific Bluetooth device."""
        try:
            om = dbus.Interface(self.bus.get_object("org.bluez", "/"), "org.freedesktop.DBus.ObjectManager")
            objects = om.GetManagedObjects()
            formatted_addr = address.replace(":", "_").upper()

            print("Searching for MediaControl1 interface...")
            for path, interfaces in objects.items():
                if "org.bluez.MediaControl1" in interfaces:
                    if formatted_addr in path:
                        print(f"Found MediaControl1 interface at: {path}")
                        media_control = dbus.Interface(
                            self.bus.get_object("org.bluez", path),
                            "org.bluez.MediaControl1"
                        )
                        return media_control
            print(f"No MediaControl1 interface found for device: {address}")
        except Exception as e:
            print(f"Failed to get MediaControl1 interface: {e}")
        return None

    def play(self, address):
        "Function for media control action play"
        try:
            control = self._get_media_control_interface(address)
            if control:
                control.Play()
                print(f"Sent Play to {address}")
        except Exception as e:
            print(f"Failed to play: {e}")

    def pause(self, address):
        "Function for media control action pause"
        try:
            control = self._get_media_control_interface(address)
            if control:
                control.Pause()
                print(f"Sent Pause to {address}")
        except Exception as e:
            print(f"Failed to pause: {e}")


    def next(self, address):
        "Function for media control action next"
        try:
            control = self._get_media_control_interface(address)
            if control:
                control.Next()
                print(f"Sent Next to {address}")
        except Exception as e:
            print(f"Failed to send Next: {e}")

    def previous(self, address):
        "Function for media control action previous"
        try:
            control = self._get_media_control_interface(address)
            if control:
                control.Previous()
                print(f"Sent Previous to {address}")
        except Exception as e:
            print(f"Failed to send Previous: {e}")

    def rewind(self, address):
        "Function for media control action rewind"
        try:
            control = self._get_media_control_interface(address)
            if control:
                control.Rewind()
                print(f"Sent Rewind to {address}")
        except Exception as e:
            print(f"Failed to send Rewind: {e}")

    def refresh_device_list(self):
        """Refresh internal list of Bluetooth devices from BlueZ."""
        self.devices.clear()
        om = dbus.Interface(self.bus.get_object("org.bluez", "/"), "org.freedesktop.DBus.ObjectManager")
        objects = om.GetManagedObjects()
        for path, interfaces in objects.items():
            if "org.bluez.Device1" in interfaces:
                props = interfaces["org.bluez.Device1"]
                address = props.get("Address")
                name = props.get("Name", "Unknown")
                uuids = props.get("UUIDs", [])
                connected = props.get("Connected", False)
                if address:
                    self.devices[address] = {
                        "Name": name,
                        "UUIDs": uuids,
                        "Connected": connected,
                    }

    def get_connected_a2dp_sink_devices(self):
        "Function to get connected a2dp sink devices"
        self.refresh_device_list()
        return {
            addr: dev["Name"]
            for addr, dev in self.devices.items()
            if dev["Connected"] and any("110b" in uuid.lower() for uuid in dev["UUIDs"])  # A2DP Sink UUID
        }

    def get_connected_a2dp_source_devices(self):
        "Function to get connected a2dp source devices"
        self.refresh_device_list()
        return {
            addr: dev["Name"]
            for addr, dev in self.devices.items()
            if dev["Connected"] and any("110a" in uuid.lower() for uuid in dev["UUIDs"])  # A2DP Source UUID
        }

    def get_connected_devices(self):
        "Function to find the connected devices so that it can be used in device selection as part of A2DP window"
        connected = {}
        bus = dbus.SystemBus()
        om = dbus.Interface(bus.get_object("org.bluez", "/"), "org.freedesktop.DBus.ObjectManager")
        objects = om.GetManagedObjects()
        for path, interfaces in objects.items():
            if "org.bluez.Device1" in interfaces:
                props = interfaces["org.bluez.Device1"]
                if props.get("Connected", False):
                    address = props.get("Address")
                    name = props.get("Name", "Unknown")
                    connected[address] = name
        return connected

    def send_file_via_obex(self, device_address, file_path):
        "Function to send file via obex using bluez"
        if not os.path.exists(file_path):
            msg = f"File does not exist: {file_path}"
            print(msg)
            return "error", msg

        try:
            session_bus = dbus.SessionBus()
            obex_service = "org.bluez.obex"
            manager_obj = session_bus.get_object(obex_service, "/org/bluez/obex")
            manager = dbus.Interface(manager_obj, "org.bluez.obex.Client1")

            # Clean up old session if it exists
            if self.last_session_path:
                try:
                    manager.RemoveSession(self.last_session_path)
                    print(f"Removed previous session: {self.last_session_path}")
                    time.sleep(1.0)
                except Exception as e:
                    print(f"Previous session cleanup failed: {e}")

            # Create a new OBEX session
            session_path = manager.CreateSession(device_address, {"Target": dbus.String("opp")})
            session_path = str(session_path)
            self.last_session_path = session_path
            print(f"Created OBEX session: {session_path}")

            # Push the file
            opp_obj = session_bus.get_object(obex_service, session_path)
            opp = dbus.Interface(opp_obj, "org.bluez.obex.ObjectPush1")
            transfer_path = opp.SendFile(file_path)
            transfer_path = str(transfer_path)
            print(f"Transfer started: {transfer_path}")

            # Monitor transfer status
            transfer_obj = session_bus.get_object(obex_service, transfer_path)
            transfer_props = dbus.Interface(transfer_obj, "org.freedesktop.DBus.Properties")

            status = "unknown"
            for _ in range(40):
                status = str(transfer_props.Get("org.bluez.obex.Transfer1", "Status"))
                print(f"Transfer status: {status}")
                if status in ["complete", "error"]:
                    break
                time.sleep(0.5)

            # Always remove session
            try:
                manager.RemoveSession(session_path)
                self.last_session_path = None
                print("Session removed after transfer.")
            except Exception as e:
                print(f"Error removing session: {e}")

            return status, f"Transfer finished with status: {status}"

        except Exception as e:
            msg = f"OBEX file send failed: {e}"
            print(msg)
            return "error", msg

    # def start_opp_receiver(self, save_directory="/tmp"):
    #     """Start an OPP server to receive files. Uses obexpushd."""
    #     try:
    #         if not os.path.exists(save_directory):
    #             os.makedirs(save_directory)
    #     # Launch obexpushd as a background process
    #         subprocess.Popen([
    #             "obexpushd",
    #             "-B",  # Bluetooth
    #             "-o", save_directory,
    #             "-n"  # No confirmation prompt
    #         ])
    #         print(f"OPP server started. Receiving files to {save_directory}")
    #         return True
    #     except Exception as e:
    #         print(f"Error starting OPP server: {e}")
    #         return False

    def start_opp_receiver(self, save_directory="/tmp"):
        """Start an OPP server to receive files. Uses obexpushd."""
        try:
            if not os.path.exists(save_directory):
                os.makedirs(save_directory)

            # Kill previous obexpushd process if already running
            if self.opp_process and self.opp_process.poll() is None:
                self.opp_process.terminate()
                self.opp_process.wait()
                print("Previous OPP server stopped.")

            # Start new obexpushd process
            self.opp_process = subprocess.Popen([
                "obexpushd",
                "-B",  # Bluetooth
                "-o", save_directory,
                "-n"  # No confirmation prompt
            ])

            print(f"OPP server started. Receiving files to {save_directory}")
            return True
        except Exception as e:
            print(f"Error starting OPP server: {e}")
            return False

    def stop_opp_receiver(self):
        """Stop the running OPP server if it's active."""
        if self.opp_process and self.opp_process.poll() is None:
            self.opp_process.terminate()
            self.opp_process.wait()
            print("OPP server stopped.")

    # def receive_file_via_obex(self,device_address,file_path):
    #     opp_obj = session_bus.get_object(obex_service,session_path)
    #     opp= dbus.Interface(opp_obj,"org.bluez.obex.ObjectPush1")
    #     transfer_path= opp.SendFile(file_path)
    #     transfer_path= str(transfer_path)
    #     try:
    #         manager.RemoveSession(session_path)
    #         self.last_session_path = None
    #         print("Session removed after transfer")
    #     except Exception as e:
    #         print(f"Error removing session: {e}")
    #
    #     return status, f"Transfer finished with status: {status}"




    # def start_opp_receiver(self, save_directory="/tmp"):
    #     """Start an OBEX OPP receiver using BlueZ OBEX Agent API."""
    #
    #     def start_agent():
    #         dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    #         agent = ObexAgent(save_path=save_directory)
    #         agent.run()
    #
    #     try:
    #         if not os.path.exists(save_directory):
    #             os.makedirs(save_directory)
    #
    #         thread = Thread(target=start_agent, daemon=True)
    #         thread.start()
    #         print(f"OBEX OPP receiver started. Files will be saved to: {save_directory}")
    #         return True
    #     except Exception as e:
    #         print(f"Error starting OPP server: {e}")
    #         return False
    #
    #

    # def start_streaming(self, audio_file):
    #     """Start A2DP streaming with the provided audio file path."""
    #     print(f"Starting A2DP streaming with file: {audio_file}")
    #     try:
    #         self.stream_process = subprocess.Popen(["aplay", audio_file])
    #         return True
    #     except Exception as e:
    #         print(f"Error while starting streaming: {e}")
    #         return False
    #
    # def stop_streaming(self):
    #     """Stop the A2DP streaming process."""
    #     print("Stopping A2DP streaming...")
    #
    #     if self.stream_process:
    #         try:
    #             self.stream_process.terminate()
    #             self.stream_process.wait()
    #             self.stream_process = None
    #             print("Streaming stopped successfully.")
    #             return True
    #         except Exception as e:
    #             print(f"Error while stopping streaming: {e}")
    #             return False
    #     else:
    #         print("No active streaming process.")
    #         return False

    # def _get_media_control_interface(self, address):
    #     """Return the MediaControl1 interface for the given device address."""
    #     try:
    #         if not address:
    #             print("No device address provided.")
    #             return None
    #         player_path = f"/org/bluez/hci0/dev_{address.replace(':', '_')}/player0"
    #         media_player = dbus.Interface(self.bus.get_object("org.bluez", player_path),"org.bluez.MediaPlayer1")
    #         return media_player
    #     except Exception as e:
    #         print(f"Failed to get MediaControl1 interface: {e}")
    #         return None





# def send_file_via_opp(self, device_address, file_path):
    #     """Send a file to a Bluetooth device using OPP (via obexftp or bt-obex)."""
    #     if not os.path.exists(file_path):
    #         print(f"File does not exist: {file_path}")
    #         return False
    #
    #     try:
    #         # Use obexctl or obexftp for sending
    #         command = [
    #             "obexftp",
    #             "--nopath",
    #             "--noconn",
    #             "--uuid", "none",
    #             "--bluetooth", device_address,
    #             "--channel", "12",  # RFCOMM channel for OPP, may vary
    #             "--put", file_path
    #         ]
    #         result = subprocess.run(command, capture_output=True, text=True)
    #         if result.returncode == 0:
    #             print(f"File sent successfully: {file_path}")
    #             return True
    #         else:
    #             print(f"Failed to send file: {result.stderr}")
    #             return False
    #     except Exception as e:
    #         print(f"Error sending file via OPP: {e}")
    #         return False

    # def send_file_via_obex(self, device_address, file_path):
    #     if not os.path.exists(file_path):
    #         print(f"File does not exist: {file_path}")
    #         return False
    #
    #     try:
    #         session_bus = dbus.SessionBus()
    #         obex_service = "org.bluez.obex"
    #         manager_obj = session_bus.get_object(obex_service, "/org/bluez/obex")
    #         manager = dbus.Interface(manager_obj, "org.bluez.obex.Client1")
    #
    #         # Clean up old session if it exists
    #         if self.last_session_path:
    #             try:
    #                 manager.RemoveSession(self.last_session_path)
    #                 print(f"Removed previous session: {self.last_session_path}")
    #                 time.sleep(1.0)
    #             except Exception as e:
    #                 print(f"Previous session cleanup failed: {e}")
    #
    #         # Create a new OBEX session
    #         session_path = manager.CreateSession(device_address, {"Target": dbus.String("opp")})
    #         session_path = str(session_path)
    #         self.last_session_path = session_path
    #         print(f"Created OBEX session: {session_path}")
    #
    #         # Push the file
    #         opp_obj = session_bus.get_object(obex_service, session_path)
    #         opp = dbus.Interface(opp_obj, "org.bluez.obex.ObjectPush1")
    #         transfer_path = opp.SendFile(file_path)
    #         transfer_path = str(transfer_path)
    #         print(f"Transfer started: {transfer_path}")
    #
    #         # Monitor transfer status
    #         transfer_obj = session_bus.get_object(obex_service, transfer_path)
    #         transfer_props = dbus.Interface(transfer_obj, "org.freedesktop.DBus.Properties")
    #
    #         for _ in range(40):
    #             status = str(transfer_props.Get("org.bluez.obex.Transfer1", "Status"))
    #             print(f"Transfer status: {status}")
    #             if status in ["complete", "error"]:
    #                 break
    #             time.sleep(0.5)
    #
    #         # Always remove session
    #         try:
    #             manager.RemoveSession(session_path)
    #             self.last_session_path = None
    #             print("Session removed after transfer.")
    #         except Exception as e:
    #             print(f"Error removing session: {e}")
    #
    #         return status == "complete"
    #
    #     except Exception as e:
    #         print(f"OBEX file send failed: {e}")
    #         return False
