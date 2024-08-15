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
    __version__ = '1.0.1'
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
        logging.info("[Polisen] loaded!")

    def on_ui_setup(self, ui):
        try:
            self._ui = ui
            # Set default position based on screen type
            # 0, 98 - Bottom left
            # 74, 112 - Bottom Row Middle

            # Use position set in options.
            if 'x-position' in self.options and 'y-position' in self.options:
                position = (
                    self.options["x-position"], 
                    self.options["y-position"]
                )
            else:
                if ui.is_waveshare_v1():
                    position = (0, 98)
                elif ui.is_waveshare_v2():
                    position = (0, 98)
                elif ui.is_waveshare_v3():
                    position = (0, 98)
                elif ui.is_waveshare144lcd():
                    position = (0, 92)
                elif ui.is_inky():
                    position = (0, 83)
                else:
                    position = (0, 98)

            ## If x & y isn't in options : add it.
            if 'x-position' not in self.options and 'y-position' not in self.options:
                x = position[0]
                y = position[1]
                self.options['x-position'] = x
                self.options['y-position'] = y

            
            if self.options['orientation'] == "vertical":
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
            else:
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
            logging.info("[Polisen] Created UI element.")
            self.polisen()
        except Exception as e:
            logging.error(f"[Polisen] An error has occurred when creating the UI: {str(e)}")


    def on_unload(self, ui):
        try:
            with ui._lock:
                ui.remove_element('polisen-ui')
                logging.info("[Polisen] Removed element.")

        except Exception as e:
            logging.error(f"[Polisen] An error has occurred: {str(e)}")


    def on_ui_update(self, ui):
        if self.news:
            ui.set('polisen-ui', self.news)
            ui.set('status', self.news)
            ui.set('face', "(^-^)")
            logging.info("[Polisen] ui has been updated!", self.news)
            self.news = ""
    
    def on_epoch(self, agent):
        logging.info("[Polisen] New epoch!")
        self.polisen()

    def polisen(self):
        try:
            logging.info(f"[Polisen] Fetching news!")
            response = requests.get("https://polisen.se/api/events", timeout=10)
            response.raise_for_status()

            if response.status_code == 200:
                data = response.json()
                if data:
                    # Regex the time from the name
                    date_match = re.search(r"([0-9]+.[0-9]+)", data[0].get('name', ''))
                    date = date_match.group(1) if date_match else 'Unknown time'
                    
                    # Get the location
                    location = data[0].get('location', {}).get('name', 'Unknown')
                    
                    # Get the type of event
                    event_type = data[0].get('type', 'Unknown')
                    
                    self.news = f"{event_type} - {location} ({date})"
                    logging.info(f"[Polisen] Fetched news: {self.news}")
                else:
                    logging.error("[Polisen] erm what, no data.")
            else:
                logging.error("[Polisen] Failed to fetch data.")

        except requests.RequestException as e:
            logging.error(f"[Polisen] An error occurred: {e}")
