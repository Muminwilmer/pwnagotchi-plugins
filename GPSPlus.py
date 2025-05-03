import json
import logging
import os

import pwnagotchi.plugins as plugins
import pwnagotchi.ui.fonts as fonts
from pwnagotchi.ui.components import LabeledValue
from pwnagotchi.ui.view import BLACK


class GPSPlus(plugins.Plugin):
    __author__ = "Mumin"
    __version__ = "1.0.1"
    __license__ = "GPL3"
    __description__ = "Saves / Shows GPS when handshakes gets captured"

    LINE_SPACING = 10
    LABEL_SPACING = 0

    def __init__(self):
        self.running = False
        self.coordinates = None
        self.options = dict()
        self.device = None
        self.elements = None

    def on_loaded(self):
        logging.info(f"[GPS] plugin loaded!")
        if not self.options.get('elements'):
            self.options["elements"] = ["lat", "lon", "alt", "sat", "fix"]
        self.elements = self.options.get('elements', [])

    def _detect_gps_device(self):
        for dev in [self.options.get("device"), "/dev/ttyUSB0", "/dev/ttyUSB1", "/dev/ttyACM0", "/dev/ttyACM1"]:
            if os.path.exists(dev):
                return dev
        return None

    def on_ready(self, agent):
        self.device = self._detect_gps_device() 

        if self.device and (os.path.exists(self.device) or ":" in str(self.device)):
            logging.info(f"[GPS] Enabling Bettercap GPS module for {self.device}")
            try:
                agent.run("gps off")
            except Exception:
                logging.debug("[GPS] Bettercap GPS module was already off")

            try:
                agent.run(f"set gps.device {self.device}")
                agent.run(f"set gps.baudrate {self.options.get('speed', '9600')}")
                agent.run("gps on")
                logging.info(f"[GPS] GPS module enabled on {self.device}")
                self.running = True
            except Exception as e:
                logging.error(f"[GPS] Failed to start GPS module: {e}")
        else:
            logging.warning("[GPS] No GPS device detected")

    def on_epoch(self, agent, epoch, epoch_data):
        if self.running:
            info = agent.session()
            gps_data = info.get("gps", {})
            if gps_data:
                self.coordinates = gps_data

    def on_handshake(self, agent, filename, access_point, client_station):
        if self.running:
            info = agent.session()
            gps_data = info.get("gps", {})
            if gps_data:
                self.coordinates = gps_data
            gps_filename = filename.replace(".pcap", ".gps.json")

            if self.coordinates and all([
                # avoid 0.000... measurements
                self.coordinates["Latitude"], self.coordinates["Longitude"]
            ]):
                logging.info(f"[GPS] saving GPS to {gps_filename} ({self.coordinates})")
                try:
                    with open(gps_filename, "w") as fp:
                        json.dump(self.coordinates, fp)
                except Exception as e:
                    logging.error(f"[GPS] Failed to save GPS data: {e}")
            else:
                logging.info("[GPS] not saving GPS. Couldn't find location.")

    def on_ui_setup(self, ui):
        # Cant bother adding every pos, please use tweak view
        for element in self.elements:
            ui.add_element(
                element,
                LabeledValue(
                    color=BLACK,
                    label=f"{element}:",
                    value="-",
                    position=(100, 100),
                    label_font=fonts.Small,
                    text_font=fonts.Small,
                    label_spacing=self.LABEL_SPACING,
                ),
            )

    def on_unload(self, ui):
        with ui._lock:
            for element in self.elements:
                ui.remove_element(element)
            logging.info("[GPS] plugin unloaded")

    def on_ui_update(self, ui):
        with ui._lock:
            try:
                if self.coordinates:
                    if "lat" in self.elements:
                        ui.set("lat", f"{self.coordinates['Latitude']:.4f}")
                    if "lon" in self.elements:
                        ui.set("lon", f"{self.coordinates['Longitude']:.4f}")
                    if "alt" in self.elements:
                        ui.set("alt", f"{self.coordinates['Altitude']}")
                    if "sat" in self.elements:
                        ui.set("sat", f"{self.coordinates['NumSatellites']}")
                    if "fix" in self.elements:
                        ui.set("fix", f"{self.coordinates['FixQuality']}")

                else:
                    for element in self.elements:
                        ui.set(element, "-")
            except Exception as e:
                logging.error(f"[GPS] Error during UI update: {e}")


