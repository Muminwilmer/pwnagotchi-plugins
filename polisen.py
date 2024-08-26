from pwnagotchi.ui.components import LabeledValue
from pwnagotchi.ui.view import BLACK
import pwnagotchi.ui.fonts as fonts
import pwnagotchi.plugins as plugins
import pwnagotchi
import logging
import requests
import re
from datetime import datetime


class Polisen(plugins.Plugin):
    __author__ = '@Muminwilmer'
    __version__ = '1.3.0'
    __license__ = 'GPL3'
    __description__ = 'Displays the latest event from the Swedish police offical API.'
    
    def on_loaded(self):
        self.city = None
        self.event = None
        self.connection = False
        # Amount of epochs between update attempts
        if 'epoch-wait' not in self.options:
            self.options['epoch-wait'] = 0
        # Only try to update while on wifi
        if 'onlyOnInternet' not in self.options:
            self.options['onlyOnInternet'] = False 
        # If true it will show the latest new event. If false it will show latest update/new event
        if 'newestEventTop' not in self.options:
            self.options['newestEventTop'] = True
        if 'twoUi' not in self.options:
            self.options['twoUi'] = True
        self.epochsWaited = 0
        logging.info("[Polisen] loaded!")

    def on_internet_available(self, agent):
        self.connection = True
        try:
            if self._ui and any(self._ui.get(ui_key) in ('No wifi', '') for ui_key in ['event-polisen-ui', 'single-polisen-ui']):
                if self.options['twoUi']:
                    self._ui.set('city-polisen-ui', "Got wifi!")
                    self._ui.set('event-polisen-ui', "Fetching news..")
                else:
                    self._ui.set('single-polisen-ui', "Got wifi Fetching..")
        except Exception as e:
            logging.error(f"[Polisen] Pre internet on fetch failed: {e}")
        try:
            logging.info(f"[Polisen] Got wifi, Fetching.")
            if self.connection:
                self.polisen()
                self.epochsWaited = 0
            else:
                logging.warning("[Polisen] No connection - Skipping epoch")
        except Exception as e:
            logging.error(f"[Polisen] Internet on fetch failed: {e}")
    
    def on_ui_setup(self, ui):
        try:
            self._ui = ui
            # Set default position based on screen type
            # 0, 97 - Bottom left
            # 74, 112 - Bottom Row Middle

            # Use position set in options.
            if ui.is_waveshare_v1() or ui.is_waveshare_v2() or ui.is_waveshare_v3():
                city_position = (0, 97)
                event_position = (0, 92)
            elif ui.is_waveshare144lcd():
                city_position = (0, 92)
                event_position = (0, 92)
            elif ui.is_inky():
                city_position = (0, 83)
                event_position = (0, 92)
            else:
                city_position = (0, 85)
                event_position = (0, 92)
            if self.options['twoUi']:
                # Add the UI element
                ui.add_element('city-polisen-ui', LabeledValue(
                        color=BLACK, label='', value='',
                        position=city_position, label_spacing=0,
                        label_font=fonts.Small, text_font=fonts.Small, max_length=20))
                # Add the UI element
                ui.add_element('event-polisen-ui', LabeledValue(
                        color=BLACK, label='', value='',
                        position=event_position, label_spacing=0,
                        label_font=fonts.Small, text_font=fonts.Small, max_length=20))
            else:
                ui.add_element('single-polisen-ui', LabeledValue(
                    color=BLACK, label='', value='',
                    position=event_position, label_spacing=0,
                    label_font=fonts.Small, text_font=fonts.Small, max_length=20))
            logging.info("[Polisen] UI element created successfully.")
            
        except Exception as e:
            logging.error(f"[Polisen] Error during UI setup: {str(e)}")

        try:
            logging.info("[Polisen] Starting data fetch.")
            self.polisen()
        except Exception as e:
            logging.error(f"[Polisen] Error while starting data fetch: {str(e)}")

    # Remove the UI element when plugin gets disabled
    def on_unload(self, ui):
        try:
            with ui._lock:
                if self.options['twoUi']:
                    ui.remove_element('city-polisen-ui')
                    ui.remove_element('event-polisen-ui')
                else:
                    ui.remove_element('single-polisen-ui')
                logging.info("[Polisen] Removed element.")

        except Exception as e:
            logging.error(f"[Polisen] An error occurred while unloading: {str(e)}")

    # Update the UI element on UI update if there's something new
    def on_ui_update(self, ui):
        try:
            if self.city:
                if self.options['twoUi']:
                    ui.set('city-polisen-ui', self.city)
                    ui.set('event-polisen-ui', self.event)
                    self.city = ""
                    self.event = ""
                else:
                    ui.set('single-polisen-ui', f"{self.city[slice(12)]} - {self.event}")
                    self.city = ""
                    self.event = ""
                ui.set('face', "(^-^)")
                logging.info("[Polisen] ui has been updated!")
                
            elif not self.connection and self.options['onlyOnInternet'] and ui.get('event-polisen-ui') == '':
                if self.options['twoUi']:
                    ui.set('event-polisen-ui', "No wifi")
                else:
                    ui.set('single-polisen-ui', "No wifi")
                
        except Exception as e:
            logging.error(f"[Polisen] Failed to update UI: {e}")

    # Fetch every epoch (depending on your settings)
    def on_epoch(self, agent, epoch, epoch_data):
        try:
            logging.info(f"[Polisen] S:{self.options['epoch-wait']} E:{self.epochsWaited}")
            if (self.options['epoch-wait'] <= self.epochsWaited):
                logging.info("[Polisen] New epoch!")
                # Will check if it has internet before starting self.polisen()
                # If check is turned off for some reason give a warning.
                if self.options['onlyOnInternet']:
                    if self.connection:
                        self.polisen()
                        self.epochsWaited = 0
                    else:
                        logging.warning("[Polisen] No connection - Skipping epoch")
                else:
                    if not self.connection:
                        logging.warning("[Polisen] No connection - trying anyways as onlyOnInternet is False!")
                    self.polisen()
                    self.epochsWaited = 0
            else: 
                logging.info(f"[Polisen] Not yet - {self.options['epoch-wait'] - self.epochsWaited} epochs left before fetching news!")
                self.epochsWaited += 1
        except Exception as e:
            logging.error(f"[Polisen] Start during epoch failed: {e}")

    # Fetches the latest event from the Swedish police official api
def polisen(self):
    try:
        logging.info(f"[Polisen] Fetching news!")
        response = requests.get("https://polisen.se/api/events", timeout=10)
        response.raise_for_status()

        if response.status_code == 200:
            data = response.json()
            if data:
                latest_event = data[0]

                if self.options['newestEventTop']:
                    latest_event = max(
                        data,
                        key=lambda event: datetime.strptime(
                            re.search(r"(\S+) (\S+) (\d+\.\d+)", event.get('name', '')).group(0),
                            f"%d %B %H.%M"
                        )
                    )

                if latest_event:
                    location = latest_event.get('location', {}).get('name', 'Unknown')
                    event_type = latest_event.get('type', 'Unknown')
                    event_time_str = re.search(r"([0-9]+.[0-9]+)", latest_event.get('name', 'Unknown')).group(1)

                    if not self.options['twoUi']:
                        location_split = location.split()
                        location = max(location_split, key=len)
                        processed_words = [
                            word[:15] if word == location else word[0]
                            for word in location_split if "län" not in word
                        ]
                        result = ' '.join(processed_words)
                        self.city = event_type
                        self.event = f"{result} ({event_time_str})"
                    else:
                        self.city = event_type
                        self.event = f"{location} ({event_time_str})"

                    logging.info("[Polisen] Fetched news")
    except requests.RequestException as e:
        logging.error(f"[Polisen] Data fetch failed: {e}")
    except Exception as e:
        logging.error(f"[Polisen] Data parsing failed: {e}")
