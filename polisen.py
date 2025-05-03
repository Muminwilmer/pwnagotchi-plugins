from pwnagotchi.ui.components import LabeledValue
from pwnagotchi.ui.view import BLACK
import pwnagotchi.ui.fonts as fonts
import pwnagotchi.plugins as plugins
import pwnagotchi
import locale
import logging
import requests
import re
from datetime import datetime


class Polisen(plugins.Plugin):
    __author__ = '@Mumin'
    __version__ = '1.3.0'
    __license__ = 'GPL3'
    __description__ = 'Displays the latest event from the Swedish police offical API.'
    
    def on_loaded(self):
        self.city = None
        self.event = None
        self.connection = False
        if 'newestEventTop' not in self.options:
            self.options['newestEventTop'] = True
        logging.info("[Polisen] loaded!")

    def on_internet_available(self, agent):
        self.connection = True
        try:
            if self._ui and any(self._ui.get(ui_key) in ('No wifi', '') for ui_key in ['event-polisen-ui']):
                self._ui.set('city-polisen-ui', "Got wifi!")
                self._ui.set('event-polisen-ui', "Fetching news..")
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
                # Add the UI element
            ui.add_element('city-polisen-ui', LabeledValue(
                    color=BLACK, label='', value='',
                    position=city_position, label_spacing=0,
                    label_font=fonts.Small, text_font=fonts.Small))
            # Add the UI element
            ui.add_element('event-polisen-ui', LabeledValue(
                    color=BLACK, label='', value='',
                    position=event_position, label_spacing=0,
                    label_font=fonts.Small, text_font=fonts.Small))
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
                ui.remove_element('city-polisen-ui')
                ui.remove_element('event-polisen-ui')
                logging.info("[Polisen] Removed element.")

        except Exception as e:
            logging.error(f"[Polisen] An error occurred while unloading: {str(e)}")

    # Update the UI element on UI update if there's something new
    def on_ui_update(self, ui):
        try:
            if self.city:
                ui.set('city-polisen-ui', self.city[slice(16)])
                ui.set('event-polisen-ui', self.event[slice(16)])
                self.city = ""
                self.event = ""
                ui.set('face', "(^-^)")
                logging.info("[Polisen] ui has been updated!")
                
            elif not self.connection and ui.get('event-polisen-ui') == '':
                ui.set('event-polisen-ui', "No wifi")
                
        except Exception as e:
            logging.error(f"[Polisen] Failed to update UI: {e}")

    # Fetch every epoch (depending on your settings)
    def on_epoch(self, agent, epoch, epoch_data):
        try:
            logging.info("[Polisen] New epoch!")

            if self.connection:
                self.polisen()
                self.epochsWaited = 0
            else:
                logging.warning("[Polisen] No connection - Skipping epoch")
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

                    #if self.options['newestEventTop']:
                    #    latest_event = max(
                    #        data,
                    #        key=lambda event: datetime.strptime(
                    #            re.search(r"(\S+) (\S+) (\d+\.\d+)", event.get('name', '')).group(0),
                    #            f"%d %B %H.%M"
                    #        )		
                    #    )
                    if self.options['newestEventTop'] == True:
                        month_translation = {
                            "januari": "January",
                            "februari": "February",
                            "mars": "March",
                            "april": "April",
                            "maj": "May",
                            "juni": "June",
                            "juli": "July",
                            "augusti": "August",
                            "september": "September",
                            "oktober": "October",
                            "november": "November",
                            "december": "December"
                        }
                        latest_time = None
                        for event in data:
                            name_str = event.get('name', '')

                            # Extracting date from the name, e.g., "15 augusti 16.55"
                            date_match = re.search(r"(\S+) (\S+) (\d+\.\d+)", name_str)   
                            if date_match:
                                day = date_match.group(1)
                                month = date_match.group(2)
                                time = date_match.group(3)
                                english_month = month_translation.get(month.lower())
                                if not english_month:
                                    logging.error("Failed month translation")
                                    continue  # Skip this event if month is unrecognized

                                date_time = f"{day} {english_month} {time}"
                                # Parsing string into a datetime object
                                event_time = datetime.strptime(date_time, "%d %B %H.%M")
                                # If latest time is smaller than the event time | make the event time the latest
                                if latest_time is None or event_time > latest_time:
                                    latest_time = event_time
                                    latest_event = event

                    if latest_event:
                        location = latest_event.get('location', {}).get('name', 'Unknown')
                        event_type = latest_event.get('type', 'Unknown')
                        event_time_str = re.search(r"([0-9]+.[0-9]+)", latest_event.get('name', 'Unknown')).group(1)

                        self.city = f"{event_type}"
                        self.event = f"{location} ({event_time_str})"

                        logging.info("[Polisen] Fetched news")
        except requests.RequestException as e:
            logging.error(f"[Polisen] Data fetch failed: {e}")
        except Exception as e:
            logging.error(f"[Polisen] Data parsing failed: {e}")
