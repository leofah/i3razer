i3 - razer
==========

*Visualize hotkeys on a Razer keyboard*

A tool to show possible hotkeys or commands (e.g. i3 or vim commands) on a Razer keyboard with rgb lighting. 
It is highly customizable: select which key is lit in which color on which action.
I encourage to write your own configuration to match your hotkeys.

Installation
============

**Disclaimer** *This program only runs on Linux, depends on the linux openrazer client and X server*

The openrazer driver can be installed from [here](https://openrazer.github.io/#download), 
just select your OS and follow the instructions.

To install i3razer run:
```
$ pip install i3razer
```
If installed with privileged rights the executable `i3razer` will already be in the path.
Otherwise it can be found in `$HOME/.local/bin`

Usage
=====

```
$ i3razer --config CONFIG
```
This runs i3razer with the given config file. Look [here](#configuration) for the configuration.
If the config is not given the [examle_config](#example-config) will be used.

```
exec --no-startup-id i3razer --config CONFIG
```
Add this line to your *i3-config* to start the visualization on i3 startup.

Contribute
==========

Find and report bugs on [github](https://github.com/leofah/i3razer).

### Map your Layout
Run `i3razer --map` to map your keyboard Layout. Consider opening a pull request with the new Layout.

Planned Features
================

- modes can have a base mode to inherit from. Useful to combine modes, e.g. mode for num\_lock on / off, 
    but still same commands
- switch mode stack: possibility to return to the previous mode and not to a defined mode (call stack instead of goto)
- dbus interface to change layout, current\_mode, reload config and a program to connect to this interface

Configuration
=============

With the configuration file the user can set the colors of keys and add keybindings to change the colors.
The file format is yaml. It consists of the sections [colors](#colors), [keys](#keys), [color\_schemes](#color-schemes), [modes](#modes)

Semantic Overview:
- Colors: define custom colors, e.g. `my_red: '0xe01010'`
- Keys: define set of keys for short access, e.g. `numbers: 0, 1, 2, 3, 4, 5, 6, 7, 8, 9`
- Color schemes: A color scheme specifies the look of the keyboard. Keys can be assigned to colors, or a color effect can be set
- Modes: Modes define, when to show which color scheme. Color schemes can be shown, depending on which keys are pressed.
    Modes can switch to another mode to change keys and color schemes
    
[Example Config](#example-config)

Colors
------

The *colors* sets values to their color name.
The definition is just `color_name: '0xrrggbb'`, where *color_ name* can be any value except starting with '0x'. 
Make sure yaml interprets *0xrrggbb* as string.

Default colors example:
```yaml
colors:
  black: '0x000000'
  red:   '0xff0000'
  green: '0x00ff00'
  blue:  '0x0000ff'
```

Keys
----

The *keys* section defines sets of keys.
When you have multiple color scheme which wants to set e.g. all numbers to the same color, the number keys can be predefined here.
The definition is `keyset_name: key_array`. For the name all values can be used except the reserved ones.

### Reserved keyset names
**all**: Predefined keyset which contains all keys of the keyboard  
**type, name, default, inherit, switch_mode, scheme**: These names have a predefined usage in the configuration.

### Key array definition
A keyarray defines multiple keys. *key_name* or *keyset_name* can be included in an array:
`key1, keyset, key2` The names are separated by ','. In a keyset definition newlines can be included.

```yaml
keys:
  prime_numbers: 2, 3, 5, 7
  numbers: 0, 1, 4, 6, 8, 9, prime_numbers # contains all numbers (0-9)
  arrows: up, left, down, right
  new_line: # newlines could improve readability
    shift_l,
    shift_r,
    control_l,
    control_r
  all: a # built in keyset, which has all keys of the keyboard
```

Color Scheme
-------------

A color scheme describes the look of the keyboard, which keys are lit in which color or what effect to play.
Which color scheme is drawn on the keyboard is determined in the *modes* section.
The default use case of a color scheme is to assign colors to keys: `keys: color`.
Keys is a [key array](#key-array-definition) (no newlines allowed) and color is either direct an hexstring '0xrrggbb' 
of a color defined in the [*colors*](#colors) section.
```yaml
color_schemes:
  my_scheme:
    all: green  # sets all keys to green
    numbers: '0xffffff' # the number keys are white
    w, a, s, d: red 
```
If a key is present in multiple key arrays, the assigned color will be the one defined latest in the file.
```yaml
# this is directly the scheme definition
override_scheme:
  a: red
  all: black # overrides the previous definition for 'a' to be red and 'a' will be shown black
``` 

### Advanced color scheme configuration
*color scheme inheritance* and *effect definition*

#### Inheritance
Maybe multiple color schemes wants to set the same colors to many keys, as the schemes are very similar.
There is no need for a redundant color scheme definition,
as it is possible to inherit from another color scheme:`inherit: color_scheme`.
This adds the color information from the inherited scheme to this scheme.

```yaml
default:
  all: green
  other_keys: yellow

gaming:
  inherit: default
  w, a, s, d: red
  
some_scheme:
  numbers: orange
  inherit: default # this overrides the numbers defined previously
```
#### Effect

To show an effect on the keyboard a color scheme *type* must be set: `type: effect`.
Possible types are: `static, breath, reactive, ripple, spectrum, starlight, wave right, wave left`
The *static* type is the default type and does not need to be specified. Each key can be assigned a static color.
All other types are keyboard build in effects, they can take a color or time, dependant on the keyboard or effect.
With these types (except *static*) inheritance is not possible,
as the definitions are quite simple and one could only inherit from the same type.
Colors of the effect are defined with `color1: white`, up to three colors can be specified.
If only one color is needed for the effect `color: white` will suffice.

##### Colors per effect:
Effect | Number of colors
------|------
breath | up to three colors
reactive | exactly one color
ripple | up to one color
starlight | up to two colors
spectrum, wave {right / left} | no color 

If no color is given the effect is always executed with a random color

##### Effect times
Some effects take a timing value: `time: value`. If no value is given, the default is used.

Effect | Time values, (default) | Description
--- | --- | ---
reactive | '500', ('1000'), '1500', '2000' | milliseconds the pressed key is lit
starlight | fast, (normal), slow | speed of starlight blinking

All other effects have no time option.

#### Example
```yaml
effect_scheme:
  type: reactive 
  color1: green # or just color: green
  time: '1000'

effect_stars:
  type: starlight
  color1: blue
  color2: green
  time: slow
```

Modes
-----

A Mode defines which color scheme gets drawn on the keyboard. The scheme depends on the currently pressed keys.
Possible hotkeys can be visualized on the keyboard, e.g. if the super key is pressed.
However sometimes the available hotkeys change, depended on what you do on your computer.
Many modes can be defined with different keys to show color schemes, but there needs to be the starting mode `default`.
Switching from one mode to another is done with hotkeys, defined in the mode.

Each mode must have a default color scheme, which will be drawn if no key is pressed: `scheme: default_scheme`. 
Displaying other color schemes is done by assigning them to hotkeys: `key_combinations: color_scheme`.

### Key Combinations
Key combinations are an array of combinations, delimited by ','.
A combination can be a single key, or multiple keys delimited by '+':  `key1 + key2`
Such a combination is pressed if all the keys in the combination are pressed.
The combination  with *nothing*: `nothing + key1 + key2` holds only if exactly key1 and key2 are pressed, 
no other key is allowed to be pressed.

If one of the combinations of the array is pressed, the whole combination array is fulfilled and the 
corresponding action applied.
If multiple combination arrays have a matching combination, the value of array defined first gets applied.

```yaml
modes:
  default: # default mode must exist, this is the start mode
    scheme: default 
    super_l + shift_l: some_scheme
    super_l: mod_scheme # also holds if super+shift is pressed, but is defined later 
    nothing + control_r, numbers: scheme # more complicated combination
```

#### Switch modes
Switching the mode gives a new default color scheme and new hotkeys. It is defined in a mode as follows:
```yaml
switch_mode:
  key_combinations: next_mode
```
#### Example

```yaml
modes:
  default:
    scheme: color/default
    super_l: super_hotkeys # light key r
    # more hotkeys
    switch_mode:
      nothing + super_l + r: mode/resize

  mode/resize:
    scheme: color/resize
    # no hotkeys to display
    switch_mode:
      nothing + escape, nothing + return: default # switch back to default mode with escape or return
```

### Example config
Here is the default [config.yaml](i3razer/example_config.yaml) which hotkeys are based on the default [i3](https://i3wm.org/) configuration.
