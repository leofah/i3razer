# set strings for the configuration file

# sections
sec_color = "colors"
sec_keys = "keys"
sec_modes = "modes"
sec_color_schemes = "color_schemes"

mode_default = "default"  # start mode
scheme_default = "scheme"  # default color scheme in mode

# fields
all_keys = "all"
field_type = "type"
field_inherit = "inherit"
field_switch = "switch_mode"
field_name = "name"  # saves name of schemes or modes

# delimiter
del_array = ","
del_combination = "+"

comb_nothing = 'nothing'  # add to key combination if JUST said keys should be pressed

# color types
type_static = "static"

type_breath = "breath"  # up to triple
type_reactive = "reactive"  # single
type_ripple = "ripple"  # single, random
type_spectrum = "spectrum"  # no color
type_starlight = "starlight"  # up to dual

type_wave_right = "wave right"  # direction
type_wave_left = "wave left"  # direction

# type options
type_color = "color"  # if set color2,3 are ignored
type_color1 = "color1"
type_color2 = "color2"
type_color3 = "color3"

type_option_time = "time"

# starlight times
time_fast = "fast"
time_normal = "normal"
time_slow = "slow"
time_s_default = time_normal

# reactive times
time_500 = "500"
time_1000 = "1000"
time_1500 = "1500"
time_2000 = "2000"  # doesn't seem to work
time_r_default = time_1000

# variable combinations
no_color_scheme_in_mode = {field_inherit, field_switch, field_name}  # fields which value is no color scheme in modes
possible_types = {type_static, type_breath, type_reactive, type_ripple, type_spectrum, type_starlight, type_wave_right,
                  type_wave_left}  # all types
no_color_in_scheme = {type_option_time, field_inherit, field_type, field_name}  # fields which value is no color

needs_color = {type_reactive}  # types where at least one color must be specified

starlight_times = {time_fast, time_normal, time_slow}
reactive_times = {time_500, time_1000, time_1500, time_2000}
