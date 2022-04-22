from logging import ERROR, getLogger
from re import split as re_split

import i3razer.config_contants as conf
from yaml import YAMLError as YamlError, safe_load as yaml_load


class ConfigParser:
    _config_file = ""
    _logger = None
    _conf_log_level = ERROR

    _configuration = dict()
    _config_integral = False  # result of the integral check after reading

    def __init__(self, config_file, logger=None):
        """
        Inits the logger and the reads the config file
        """
        if not logger:
            logger = getLogger(__name__)
        self._logger = logger
        self.read(config_file)

    def is_integral(self):
        """
        return: True -> correct config
            False -> error in config
        """
        return self._config_integral

    def read(self, config_file=None):
        """
        reads razer config from file
        if no file given, the old file will be read
        return: False if errors in config file or file not found
        """
        if not config_file:
            config_file = self._config_file
        self._config_file = config_file

        # read file
        try:
            with open(config_file, 'r') as file:
                try:
                    self._configuration = yaml_load(file)
                except YamlError as e:
                    self._logger.error(f"Yaml Error: {e}")
                    return False
        except FileNotFoundError:
            self._logger.error(f"Config file '{config_file}' not found")
            return False

        # process
        self._to_lower_case()
        if not self._check_integrity():
            return False
        self._add_fields()
        return True

    def _to_lower_case(self):
        """
        sets all end values in the config to lower case and converts them to strings
        """
        self._configuration = self._lower_case_helper(self._configuration)
        pass

    def _lower_case_helper(self, value):
        """
        recursive helper for lower case
        """
        if isinstance(value, dict):
            result = {}
            for sec in value:
                result[str(sec).lower()] = self._lower_case_helper(value[sec])
            return result
        return str(value).lower()

    def _check_integrity(self) -> bool:
        """
        checks the integrity of the config file:
            - all needed sections are given
            - default mode given
            - no invalid value set (timing, color)
            - all referenced modes/schemes/keysets are defined in their section
        Error messages are logged in logger with level self._conf_log_level
        """
        res = True
        c = self._configuration

        is_mode = {}  # mode: defined in mode
        is_scheme = {}  # scheme: defined in ...
        is_color = {}  # color: defined in ...
        is_keyset = set()

        inheriting = {}  # find loop in inheriting. section: {name: depends on}

        # check modes section
        if conf.sec_modes not in c:
            self._logger.log(self._conf_log_level, f"No Section '{conf.sec_modes} in config file")
            res = False
        else:
            modes = c[conf.sec_modes]
            if conf.mode_default not in modes:
                self._logger.log(self._conf_log_level, f"No Default mode '{conf.mode_default}' in modes section")
                res = False
            for mode_name in modes:
                # check each mode for correct definition
                mode = modes[mode_name]
                if conf.scheme_default not in mode:
                    self._logger.log(self._conf_log_level,
                                     f"Mode {mode_name} has no default color scheme (Field: {conf.scheme_default})")
                    res = False
                for field in mode:
                    # check the fields of the mode
                    if field == conf.field_switch:
                        for switch in mode[field]:
                            # field name is not checked as this can be key sets, arrays, combinations or single keys
                            # single key names are not known, so invalid key cannot be detected
                            is_mode[mode[field][switch]] = f"switch mode with {switch} in mode {mode_name}"

                    if field in conf.no_color_scheme_in_mode:
                        continue
                    # every other field has a color scheme as value
                    is_scheme[mode[field]] = f"'{field}' in Mode {mode_name}"

        # check color schemes section
        if conf.sec_color_schemes not in c:
            self._logger.log(self._conf_log_level, f"No Section '{conf.sec_color_schemes}' in config file")
            res = False
        else:
            inherit = {}
            for scheme_name in c[conf.sec_color_schemes]:
                # check each color scheme
                scheme = c[conf.sec_color_schemes][scheme_name]
                # check if correct type
                if conf.field_type in scheme:
                    scheme_type = scheme[conf.field_type]
                    if scheme_type not in conf.possible_types:
                        self._logger.log(self._conf_log_level,
                                         f"type {scheme_type} in scheme '{scheme_name}' is invalid")
                        res = False
                    # scheme types specific checks: correct time
                    elif scheme_type == conf.type_reactive:
                        if conf.type_option_time in scheme:
                            time = scheme[conf.type_option_time]
                            if time not in conf.reactive_times:
                                self._logger.log(self._conf_log_level,
                                                 f"time '{time}' is no reactive time in scheme '{scheme_name}'"
                                                 f"possible times are: {conf.reactive_times}")
                                res = False
                    elif scheme_type == conf.type_starlight:
                        if conf.type_option_time in scheme:
                            time = scheme[conf.type_option_time]
                            if time not in conf.starlight_times:
                                self._logger.log(self._conf_log_level,
                                                 f"time '{time}' is no starlight time in scheme '{scheme_name}'"
                                                 f"possible times are: {conf.starlight_times}")
                                res = False
                    # check if colors are given for specific types
                    if scheme_type in conf.needs_color:
                        if conf.type_color not in scheme and conf.type_color1 not in scheme:
                            self._logger.log(self._conf_log_level,
                                             f"Type '{scheme_type}' in scheme '{scheme_name}' needs "
                                             f"to set a color ({conf.type_color} or {conf.type_color}")
                            res = False
                for field in scheme:
                    # check each field
                    if field == conf.field_inherit:
                        inherit[scheme_name] = {scheme[field]}
                        is_scheme[scheme[field]] = f"Inherit in scheme {scheme_name}"

                    if field in conf.no_color_in_scheme:
                        continue
                    # every other field has a color as value
                    is_color[scheme[field]] = f"Key {field} in scheme {scheme_name}"
            inheriting["schemes"] = inherit

        # check colors section
        if conf.sec_color not in c:
            self._logger.log(self._conf_log_level, f"No Section '{conf.sec_color}' in config file")
            res = False
        else:
            colors = c[conf.sec_color]
            for color_name in colors:
                # check for correct color definiton
                color = colors[color_name]
                if not isinstance(color, str) or not color.startswith("0x"):
                    self._logger.log(self._conf_log_level, f"Invalid color definition: {color_name}: {color}")
                    res = False

        # check keys section
        if conf.sec_keys not in c:
            self._logger.log(self._conf_log_level, f"No Section '{conf.sec_keys}' in config file")
            res = False
        else:
            keys = c[conf.sec_keys]
            if not isinstance(keys, dict):
                self._logger.log(self._conf_log_level, f"Section Keys is no dictionary")
                res = False
            else:
                # check for loops in key definiton via inheriting variable
                is_keyset = keys.keys()
                inherit = {}
                for keyset in keys:
                    inherit[keyset] = set()
                    # find keysets in the array
                    for key in re_split('[,+\n]', keys[keyset]):
                        key = key.strip()
                        if key in is_keyset:
                            inherit[keyset].add(key)
                inheriting["keysets"] = inherit

        # test is_...
        # mode
        if conf.sec_modes in c:
            modes = c[conf.sec_modes]
            for mode in is_mode:
                if mode not in modes:
                    self._logger.log(self._conf_log_level, f"Mode '{mode}' not defined. ({is_mode[mode]})")
                    res = False

        # scheme
        if conf.sec_color_schemes in c:
            schemes = c[conf.sec_color_schemes]
            for scheme in is_scheme:
                if scheme not in schemes:
                    self._logger.log(self._conf_log_level,
                                     f"Color Scheme '{scheme}' not defined. ({is_scheme[scheme]})")
                    res = False

        # color
        if conf.sec_color in c:
            colors = c[conf.sec_color]
            for color in is_color:
                if not isinstance(color, str) or (not color.startswith("0x") and color not in colors):
                    self._logger.log(self._conf_log_level, f"Invalid color '{color}' ({is_color[color]})")
                    res = False

        # infinite loop test
        for x in inheriting:
            old_inherit = {}
            new_inherit = inheriting[x]
            # Follow inherit line as far as possible
            while old_inherit != new_inherit:
                old_inherit = new_inherit.copy()
                for name in old_inherit:
                    for key in old_inherit[name]:
                        if key in old_inherit:
                            new_inherit[name] = new_inherit[name].union(old_inherit[key])
            # expanded all lines, check for loop
            logged_loops = set()
            for name in old_inherit:
                if name in old_inherit[name]:
                    if old_inherit[name] not in logged_loops:
                        self._logger.log(self._conf_log_level, f"Inherit Loop in {x} detected: {old_inherit[name]}")
                        logged_loops.add(frozenset(old_inherit[name]))
                    res = False

        # keyset definitions are not checked, as it is not clear which keys are in the layout
        self._config_integral = res
        return res

    def _add_fields(self):
        """
        adds the field name to modes and color schemes
        adds to color scheme the field type=static if not set
        """
        # integrity check done so mode and color scheme should be present
        # modes
        for mode_name in self._configuration[conf.sec_modes]:
            self._configuration[conf.sec_modes][mode_name][conf.field_name] = mode_name
        # color schemes
        for scheme_name in self._configuration[conf.sec_color_schemes]:
            scheme = self._configuration[conf.sec_color_schemes][scheme_name]
            scheme[conf.field_name] = scheme_name
            if conf.field_type not in scheme:
                scheme[conf.field_type] = conf.type_static

    def get_color(self, color):
        """
        decodes the given color, by looking it up in the colors section and calculation r, g, b values
        """
        if color.startswith("0x"):
            maybe_color_code = color
        else:
            if color in self._configuration["colors"]:
                maybe_color_code = self._configuration["colors"][color]
            else:
                self._logger.warning(f"Color '{color}' not defined in config file")
                return
        try:
            color_code = int(maybe_color_code, 0)
        except ValueError:
            self._logger.warning(f"color '{color}' invalid")
            return 0, 0, 0
        razer_color = ((color_code // 256 // 256) % 256, (color_code // 256) % 256, color_code % 256)
        return razer_color

    # avoiding infinite loops
    _checking_keysets = set()

    def get_keys(self, name):
        """
        decodes all keys from a given name, splits arrays and follows key set definitons
        """
        keys = self._get_keys_single(name)
        keys = keys.union(self._get_keys_array(name))
        return keys.union(self._get_keys_referenced(name))

    def _get_keys_single(self, name):
        """
        will return the name as {key}, if it is split as far as possible
        """
        if name in self._configuration[conf.sec_keys] or conf.del_array in name:
            return set()
        return {name}

    def _get_keys_array(self, array):
        """
        if array is a key array, this returns the all keys in the keyarray, also the referenced one in the key section
        """
        # multiple keys or keysets are separated by an comma
        keys = set()
        if conf.del_array in array:
            keys = {k.strip() for k in set(array.replace("\n", "").split(conf.del_array))}
        else:
            return keys
        # not each array entry is directly a key, need to resolve these recursively
        # arrays gets shorter so not stackoverflow possible
        resolved_keys = set()
        for key in keys:
            resolved_keys = resolved_keys.union(self.get_keys(key))
        return resolved_keys

    def _get_keys_referenced(self, reference):
        """
        resolves a reference name (defined in section keys) to its corresponding keys
        Also done recursively by calling get_keys
        """
        if reference == conf.all_keys:
            # all is a build in reference which gets resolved on drawing
            return
        keys = set()
        if reference in self._configuration[conf.sec_keys]:
            if reference in self._checking_keysets:
                # reference loop detected
                self._logger.warning(f"Keys {reference} occur in an infinite loop")
                return keys
            self._checking_keysets.add(reference)
            keys = self.get_keys(self._configuration[conf.sec_keys][reference])
            self._checking_keysets.remove(reference)
        return keys

    def _get_combination_value(self, pressed_keys, options):
        """
        selects the correct option for the pressed keys
        """
        # keys can be defined as arrays or keylists as 'or' pressed keys.
        # if the list is 'key1 + key2' both keys must be pressed ('and')
        # special: 'nothing + key1 + key2' only holds if JUST key1 and key2 are pressed
        # precedence is from top to bottom, so on extra handling
        for option_keys in options:
            keys = self.get_keys(option_keys)
            for key_comb in keys:
                combination = {k.strip() for k in key_comb.split(conf.del_combination)}
                if conf.comb_nothing in combination:
                    # special case, JUST set keys should be pressed
                    combination.remove(conf.comb_nothing)
                    if pressed_keys == combination:
                        return options[option_keys]
                else:
                    if combination <= pressed_keys:
                        return options[option_keys]
        # if no combination matched None is returned

    def get_important_keys_mode(self, mode):
        """
        keys to listen to when in given mode
        """
        keys = set()
        for field in mode:
            if field == conf.field_switch:
                for switch_comb in mode[conf.field_switch]:
                    keys = keys.union(self._get_all_keys(switch_comb))
            elif field in conf.no_color_scheme_in_mode or field == conf.scheme_default:
                continue
            else:
                keys = keys.union(self._get_all_keys(field))
        return keys

    def _get_all_keys(self, key_array):
        """
        return all the keys in an array, either referenced or in a combination
        differs from get_keys, because it also splits combinations
        """
        keys = set()
        key_combs = self.get_keys(key_array)
        for comb in key_combs:
            for key in comb.split(conf.del_combination):
                keys.add(key.strip())
        return keys

    def get_color_scheme(self, pressed_keys, mode):
        """
        returns color scheme to display, when *pressed_keys* are pressed in given mode
        """
        scheme_name = self._get_combination_value(pressed_keys, mode)
        if not scheme_name:
            scheme_name = mode[conf.scheme_default]
        return self.get_color_scheme_by_name(scheme_name)

    def get_next_mode(self, pressed_keys, current_mode):
        """
        return the mode to switch to, when *pressed_keys* are pressed in given mode
        """
        next_mode_name = self._get_combination_value(pressed_keys, current_mode[conf.field_switch])
        if not next_mode_name:
            return current_mode
        return self.get_mode_by_name(next_mode_name)

    def get_color_scheme_by_name(self, name):
        """
        returns the named color scheme, when present
        """
        if name in self._configuration[conf.sec_color_schemes]:
            return self._configuration[conf.sec_color_schemes][name]
        self._logger.error(f"color scheme {name} not found")

    def get_mode_by_name(self, name):
        """
        return the named mode, when present
        """
        if name in self._configuration[conf.sec_modes]:
            return self._configuration[conf.sec_modes][name]
        self._logger.warning(f"mode {name} not found")
