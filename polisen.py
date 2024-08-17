from pwnagotchi.ui.components import LabeledValue
from pwnagotchi.ui.view import BLACK
import pwnagotchi.ui.fonts as fonts
import pwnagotchi.plugins as plugins
import pwnagotchi
import logging
import requests
import re


class Polisen(plugins.Plugin):
    __author__ = '@Muminwilmer'
    __version__ = '1.1.1'
    __license__ = 'GPL3'
    __description__ = 'Displays the latest event from the Swedish police offical API.'

    # EXAMPLE RESPONSE ->
    # "id": 542272,
    # "datetime": "2024-08-15 17:47:48 +02:00",
    # "name": "15 augusti 16.55, Bråk, Västerås",   -   (Used for time: 16.55)
    # "summary": "Samtal om pågående bråk.",
    # "url": "/aktuellt/handelser/2024/augusti/15/15-augusti-16.55-brak-vasteras/",
    # "type": "Bråk",   -   (Used for type: Bråk)
    # "location": {
    #     "name": "Västerås",   -   (Used for location: Västerås)
    #     "gps": "59.609901,16.544809"
    # }
    
    def on_loaded(self):
        self.news = None
        self.connection = False
        if 'epoch-wait' not in self.options:
            self.options['epoch-wait'] = 0
        if 'onlyOnInternet' not in self.options:
            self.options['onlyOnInternet'] = True
        self.epochsWaited = 0
        logging.info("[Polisen] loaded!")

    def on_internet_available(self, agent):
        self.connection = True
    
    def on_ui_setup(self, ui):
        try:
            self._ui = ui
            # Set default position based on screen type
            # 0, 98 - Bottom left
            # 74, 112 - Bottom Row Middle

            # Use position set in options.
            if 'x-position' in self.options and 'y-position' in self.options:
                position = (self.options["x-position"], self.options["y-position"])
            else:
                if ui.is_waveshare_v1() or ui.is_waveshare_v2() or ui.is_waveshare_v3():
                    position = (0, 98)
                elif ui.is_waveshare144lcd():
                    position = (0, 92)
                elif ui.is_inky():
                    position = (0, 83)
                else:
                    position = (0, 98)
                self.options['x-position'], self.options['y-position'] = position

            # Add the UI element
            ui.add_element(
                'polisen-ui',
                LabeledValue(
                    color=BLACK,
                    label='',
                    value='',
                    position=position,
                    label_font=fonts.Bold,
                    text_font=fonts.Small
                )
            )
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
                ui.remove_element('polisen-ui')
                logging.info("[Polisen] Removed element.")

        except Exception as e:
            logging.error(f"[Polisen] An error occurred while unloading: {str(e)}")

    # Update the UI element on UI update if there's something new
    def on_ui_update(self, ui):
        try:
            if self.news:
                ui.set('polisen-ui', self.news)
                ui.set('status', self.news)
                ui.set('face', "(^-^)")
                logging.info("[Polisen] ui has been updated!", self.news)
                self.news = ""
        except Exception as e:
            logging.error(f"[Polisen] Failed to update UI: {e}")

    # Fetch every epoch (depending on your settings)
    def on_epoch(self, agent, epoch, epoch_data):
        try:
            if (self.options['epoch-wait'] >= self.epochsWaited):
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
                    if self.connection:
                        self.polisen()
                    else:
                        logging.warning("[Polisen] No connection - trying anyways as onlyOnInternet is False!")
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
                    date_match = re.search(r"([0-9]+.[0-9]+)", data[0].get('name', ''))
                    date = date_match.group(1) if date_match else 'Unknown time'
                    location = data[0].get('location', {}).get('name', 'Unknown')
                    event_type = data[0].get('type', 'Unknown')
                    self.news = f"{event_type} - {location} ({date})"
                    logging.info(f"[Polisen] Fetched news: {self.news}")
        except requests.RequestException as e:
            logging.error(f"[Polisen] Data fetch failed: {e}")
        except Exception as e:
            logging.error(f"[Polisen] Data parsing failed: {e}")
