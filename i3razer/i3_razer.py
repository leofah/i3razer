from logging import getLogger

from openrazer.client import DaemonNotFound, DeviceManager, constants as razer_constants

from i3razer import config_contants as conf
from i3razer.config_parser import ConfigParser
from i3razer.layout import layouts
from i3razer.pyxhook import HookManager

ERR_DAEMON_OFF = -2  # openrazer is not running
ERR_NO_KEYBOARD = -3  # no razer keyboard found
ERR_CONFIG = -4  # Error in config file


class I3Razer:
    _logger = None

    # Keyboard settings
    _serial = ""
    _keyboard = None
    _key_layout = {}
    _key_layout_name = ""  # Only present if layout is set manually

    # handle modes and keys
    _listen_to_keys = set()  # the keys which could change the displayed color scheme
    _current_pressed_keys = set()
    _current_scheme_name = ""
    _mode = None

    _config = None
    _drawing_scheme = set()  # prevent infinite inherit loop in color schemes

    # Thread handling
    _hook = None
    _running = False

    def __init__(self, config_file, layout=None, logger=None):
        """
        config_file: path to the config file
        layout: keyboard Layout to use for lighting the keys. If none is given it is detected automatically
        logger: Logger to use for logging
        """
        if not logger:
            logger = getLogger(__name__)
        self._logger = logger
        self._logger.info("Loading config")
        self._load_config(config_file)
        self._logger.info("Loading Razer Keyboard")
        self._load_keyboard(layout)
        self._logger.info("Loading done")

    def _update_color_scheme(self):
        """
        Determines which color scheme should be displayed and displays it
        """
        if self._running:
            if not self._mode:
                self._mode = self._config.get_mode_by_name(conf.mode_default)
                self._listen_to_keys = self._config.get_important_keys_mode(self._mode)
            self._logger.debug(f"pressed keys: {self._current_pressed_keys} in mode {self._mode[conf.field_name]}")

            # find mode
            next_mode = self._config.get_next_mode(self._current_pressed_keys, self._mode)
            if next_mode[conf.field_name] != self._mode[conf.field_name]:
                # swapped to a new mode
                self._mode = next_mode
                self._listen_to_keys = self._config.get_important_keys_mode(self._mode)

            # update color scheme for mode
            scheme = self._config.get_color_scheme(self._current_pressed_keys, self._mode)
            self._draw_color_scheme(scheme)

    def _draw_color_scheme(self, color_config):
        """
        draw the given color scheme
        """
        if self._current_scheme_name == color_config[conf.field_name]:
            return
        # parse type
        if conf.field_type in color_config:
            if color_config[conf.field_type] == conf.type_static:
                self._draw_static_scheme(color_config)
            else:
                self._draw_color_effect(color_config)
        else:
            self._draw_static_scheme(color_config)

        self._current_scheme_name = color_config[conf.field_name]
        self._logger.info(f"Drawn color scheme '{color_config[conf.field_name]}'")

    def _draw_color_effect(self, color_config):
        """
        Draw an effect color scheme
        """
        if conf.field_type not in color_config:
            return
        effect_type = color_config[conf.field_type]
        fx = self._keyboard.fx

        # find colors for effect
        color1, color2, color3 = None, None, None
        nr_colors = 0
        if conf.type_color in color_config:
            color1 = self._config.get_color(color_config[conf.type_color])
            nr_colors = 1
        elif conf.type_color1 in color_config:
            color1 = self._config.get_color(color_config[conf.type_color1])
            nr_colors = 1
            if conf.type_color2 in color_config:
                color2 = self._config.get_color(color_config[conf.type_color2])
                nr_colors = 2
                if conf.type_color3 in color_config:
                    color3 = self._config.get_color(color_config[conf.type_color3])
                    nr_colors = 3

        # huge switch through all modes -----------------------------------------------------------------
        # breath
        if effect_type == conf.type_breath:
            if nr_colors >= 3 and fx.has("breath_triple"):
                fx.breath_triple(color1[0], color1[1], color1[2], color2[0], color2[1], color2[2], color3[0], color3[1],
                                 color3[2])
            elif nr_colors >= 2 and fx.has("breath_dual"):
                fx.breath_dual(color1[0], color1[1], color1[2], color2[0], color2[1], color2[2])
            elif nr_colors >= 1 and fx.has("breath_single"):
                fx.breath_single(color1[0], color1[1], color1[2])
            elif nr_colors >= 0:
                fx.breath_random()

        # reactive
        elif effect_type == conf.type_reactive:
            if not fx.has("reactive"):
                self._logger.warning(f"reactive not supported by keyboard {self._keyboard.name}")
                return
            if not color1:
                self._logger.warning(f"No color for reactive set in {color_config[conf.field_name]}")
                return
            time = conf.time_r_default
            if conf.type_option_time in color_config:
                time = color_config[conf.type_option_time]
            razer_time = razer_constants.REACTIVE_500MS if time == conf.time_500 \
                else razer_constants.REACTIVE_1000MS if time == conf.time_1000 \
                else razer_constants.REACTIVE_1500MS if time == conf.time_1500 \
                else razer_constants.REACTIVE_2000MS if time == conf.time_2000 \
                else None
            fx.reactive(color1[0], color1[1], color1[2], razer_time)

        # ripple
        elif effect_type == conf.type_ripple:
            if not fx.has("ripple"):
                self._logger.warning(f"ripple not supported by keyboard {self._keyboard.name}")
                return
            if color1:
                fx.ripple(color1[0], color1[1], color1[2], razer_constants.RIPPLE_REFRESH_RATE)
            else:
                fx.ripple_random(razer_constants.RIPPLE_REFRESH_RATE)

        # spectrum
        elif effect_type == conf.type_spectrum:
            if not fx.has("spectrum"):
                self._logger.warning(f"spectrum not supported by keyboard {self._keyboard.name}")
                return
            fx.spectrum()

        # starlight
        elif effect_type == conf.type_starlight:
            time = conf.time_s_default
            if conf.type_option_time in color_config:
                time = color_config[conf.type_option_time]
            razer_time = razer_constants.STARLIGHT_FAST if time == conf.time_fast \
                else razer_constants.STARLIGHT_NORMAL if time == conf.time_normal \
                else razer_constants.STARLIGHT_SLOW if time == conf.time_slow \
                else None
            if nr_colors >= 2 and fx.has("starlight_dual"):
                fx.starlight_dual(color1[0], color1[1], color1[2], color2[0], color2[1], color2[2], razer_time)
            elif nr_colors >= 1 and fx.has("starlight_single"):
                fx.starlight_single(color1[0], color1[1], color1[2], razer_time)
            elif nr_colors >= 0:
                fx.starlight_random(razer_time)

        # wave right
        elif effect_type == conf.type_wave_right:
            fx.wave(razer_constants.WAVE_RIGHT)

        # wave left
        elif effect_type == conf.type_wave_left:
            fx.wave(razer_constants.WAVE_LEFT)

        else:
            self._logger.warning(f"type '{effect_type}' is not known")

        # switch finished

    def _draw_static_scheme(self, color_config):
        """
        draw a static color scheme
        """
        # One could save the result matrix to be faster on a following draw
        self._keyboard.fx.advanced.matrix.reset()
        self._add_to_static_scheme(color_config)
        self._keyboard.fx.advanced.draw()

    def _add_to_static_scheme(self, color_config):
        """
        Adds inherited color schemes on display matrix
        """
        # assert scheme type is static
        if color_config[conf.field_type] != conf.type_static:
            self._logger.warning(f"trying to inherit a non static color scheme '{color_config[conf.field_name]}")
            return

        # handle infinite loop
        name = color_config[conf.field_name]
        if name in self._drawing_scheme:
            # should be detected on reading config
            self._logger.warning(f"color scheme '{name}' is in an inherit loop with {self._drawing_scheme}")
            return
        self._drawing_scheme.add(name)

        # set colors
        for field in color_config:
            # handle "inherit
            if field == conf.field_inherit:
                add_scheme = self._config.get_color_scheme_by_name(color_config[conf.field_inherit])
                self._add_to_static_scheme(add_scheme)
                continue

            # non color fields
            if field in conf.no_color_in_scheme:
                continue

            # handle "all"
            if field == conf.all_keys:
                keys = self._key_layout.keys()
            else:
                # field is a key array
                keys = self._config.get_keys(field)
            if keys:
                color = self._config.get_color(color_config[field])
                self._set_color(color, keys)

        self._drawing_scheme.remove(name)

    def _set_color(self, color, keys):
        for key in keys:
            if key in self._key_layout:
                self._keyboard.fx.advanced.matrix[self._key_layout[key]] = color
            else:
                self._logger.warning(f"Key '{key}' not found in Layout")

    def _load_keyboard(self, layout):
        """
        Load Keyboard on startup
        """
        self._key_layout_name = layout
        if not self.reload_keyboard():
            self._logger.critical("No Razer Keyboard found")
            exit(ERR_NO_KEYBOARD)

    def _setup_key_hook(self):
        """
        Setup pyxhook to recognize key presses
        """

        def on_key_pressed(event):
            # Key pressed, update scheme if needed
            key = event.Key.lower()  # config is in lower case
            if key not in self._current_pressed_keys:
                self._current_pressed_keys.add(key)
                if key in self._listen_to_keys:
                    self._update_color_scheme()

        def on_key_released(event):
            key = event.Key.lower()
            if key in self._current_pressed_keys:
                self._current_pressed_keys.remove(key)
            else:
                self._logger.warning(
                    f"releasing key {key} not in pressed keys {self._current_pressed_keys}, resetting pressed keys")
                self._current_pressed_keys = set()
            if key in self._listen_to_keys:
                self._update_color_scheme()

        # init hook manager
        hook = HookManager()
        hook.KeyDown = on_key_pressed
        hook.KeyUp = on_key_released
        self._hook = hook

    def _load_config(self, config_file):
        """
        Load config on startup
        """
        self._config = ConfigParser(config_file, self._logger)
        if not self._config.is_integral():
            self._logger.critical("Error while loading config file")
            exit(ERR_CONFIG)

    ###############################################
    # public methods to change or query the state #
    ###############################################

    def start(self):
        """
        Start the shortcut visualisation. This starts a new Thread.
        Stop this by calling stop() on the object.
        """
        if not self._running:
            self._logger.warning("Starting Hook")
            self._setup_key_hook()
            self._hook.start()
            self._running = True
            self._update_color_scheme()

    def stop(self):
        """
        stops the program by stopping the internal thread waiting for keyboard events
        """
        if self._running:
            self._logger.warning(f"Stopping hook")
            self._running = False
            self._hook.cancel()
            self._hook = None

    def reload_config(self, config_file=None) -> bool:
        """
        Loads a new config file and updates color_scheme accordingly
        return: False if error in config
        """
        if not self._config.read(config_file):
            self._logger.error(f"Error in config, using old config file")
            return False
        self.force_update_color_scheme()
        return True

    def reload_keyboard(self, layout=None) -> bool:
        """
        Reloads to the computer connected keyboards, and could set an layout
        return: true if a razer keyboard was loaded
        """
        try:
            device_manager = DeviceManager()
        except DaemonNotFound:
            self._logger.critical("Openrazer daemon not running")
            exit(ERR_DAEMON_OFF)
        for device in device_manager.devices:
            if device.type == "keyboard":
                self._keyboard = device
                break

        if self._keyboard:
            if layout:
                self._key_layout_name = layout
            device_manager.sync_effects = False
            self._serial = str(self._keyboard.serial)
            self.load_layout(self._key_layout_name)
        else:
            self._logger.error("no razer keyboard found")
            return False
        self._logger.info(f"successfully loaded Keyboard {self._keyboard.name}")
        return True

    def load_layout(self, layout_name=None) -> bool:
        """
        Loads the named layout for the current keyboard. If none is named, the layout is detected automatically
        returns False if the layout cannot be found, the layout is not changed
        """
        # Keysyms have a new map if layout changed
        if self._hook:
            self._hook.reset_keysyms()

        no_layout = False  # flow control
        if not layout_name:
            no_layout = True
            if self._keyboard:
                layout_name = self._keyboard.keyboard_layout
                self._logger.info(f"Detected Layout {layout_name}")
        if layout_name not in layouts and no_layout:
            self._logger.error(f"Layout {layout_name} not found, using default 'en_US'")
            layout_name = "en_US"  # en_US is default and in layout.py

        if layout_name in layouts:
            # Load the layout
            self._key_layout = layouts[layout_name]
            self._logger.info(f"Loaded keyboard layout {layout_name}")
            return True

    def change_mode(self, mode_name: str) -> bool:
        """
        changes the current mode to the given one and updates the scheme
        return: False if mode does not exist in config
        """
        new_mode = _mode = self._config.get_mode_by_name(mode_name)
        if new_mode:
            self._mode = new_mode
            self._listen_to_keys = self._config.get_important_keys_mode(self._mode)
            self._update_color_scheme()
            return True
        return False

    def get_mode_name(self) -> str:
        """
        returns the name of the current mode
        """
        if self._mode:
            return self._mode[conf.field_name]
        else:
            # if no mode loaded, return default name
            return conf.mode_default

    def change_color_scheme(self, color_scheme_name: str) -> bool:
        """
        changes the displayed color scheme. On the next keypress, the old associated color scheme is shown again.
        Works also if the thread is not started yet, then the scheme does not change on a keypress
        return: false if the color scheme cannot be found
        """
        color_config = self._config.get_color_scheme_by_name(color_scheme_name)
        if not color_config:
            return False
        self._draw_color_scheme(color_config)
        return True

    def get_color_scheme_name(self) -> str:
        """
        returns the current drawn color scheme
        """
        return self._current_scheme_name

    def force_update_color_scheme(self):
        """
        deletes internal variables and detects which color scheme to show
        """
        self._current_scheme_name = ""
        self._update_color_scheme()
