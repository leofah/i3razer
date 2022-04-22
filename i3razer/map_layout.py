from pprint import pprint

from i3razer.layout import layouts
from i3razer.pyxhook import HookManager
from openrazer.client import DeviceManager


def map_layout():
    MapLayout()


class MapLayout:
    """
    Maps the keyboard layout. The pressed keys are detected with pyxhook, to get the correct names
    """
    device_manager = None
    hook = None

    current_keyboard_layout = {}
    all_layouts = layouts

    finished_keyboards = 0

    # current keyboard positions
    keyboard = None
    name = ""
    layout = ""
    row = 0
    column = 0
    rows = 0
    columns = 0

    blue = (0, 0, 255)
    green = (0, 255, 0)

    def __init__(self):
        """
        Start the mapping with all keyboard
        """
        self.information()
        self.init_device_manager()
        self.start_hook()

    def init_device_manager(self):
        self.device_manager = DeviceManager()
        # Disable daemon effect syncing.
        # Without this, the daemon will try to set the lighting effect to every device.
        self.device_manager.sync_effects = False
        if not self.device_manager.devices:
            print(f"No Keyboard found")
            exit()
        print(f"Found {len(self.device_manager.devices)} Razer devices")
        self.init_keyboard(self.device_manager.devices[0])

    def init_keyboard(self, keyboard):
        """
        prepare class variables for given keyboard
        """
        self.keyboard = keyboard
        self.name = keyboard.name
        self.layout = keyboard.keyboard_layout
        self.rows = keyboard.fx.advanced.rows
        self.columns = keyboard.fx.advanced.cols

        self.row = 0
        self.column = 0
        print(f"Next Keyboard: {self.name}")
        print(f"({self.row}, {self.column})")

        # assume escape is on position (0, 1)
        self.current_keyboard_layout["escape"] = (0, 1)

        keyboard.fx.advanced.matrix.reset()
        keyboard.fx.advanced.matrix[self.row, self.column] = self.green
        keyboard.fx.advanced.draw()

    def next_keyboard(self):
        """
        One keyboard is done, save results and load new keyboard
        """
        print(f"keyboard {self.name} finished:")
        self.all_layouts[self.layout] = self.current_keyboard_layout
        self.current_keyboard_layout = {}
        self.finished_keyboards += 1
        if len(self.device_manager.devices) == self.finished_keyboards:
            self.finish()
        else:
            self.init_keyboard(self.device_manager.devices[self.finished_keyboards])

    def next_key(self):
        """
        A Key was pressed.
        Update the colors on the keyboard and handle the current keyboard position
        """
        # key done: color blue
        self.keyboard.fx.advanced.matrix[self.row, self.column] = self.blue
        self.column += 1
        if self.column == self.columns:
            self.column = 0
            self.row += 1
            if self.row == self.rows:
                self.next_keyboard()
        # next key: green
        print(f"({self.row}, {self.column})")
        self.keyboard.fx.advanced.matrix[self.row, self.column] = self.green
        self.keyboard.fx.advanced.draw()

    def start_hook(self):
        def on_key_pressed(event):
            key = event.Key.lower()
            if key != "escape":  # escape is used to jump to the next key, its position is know
                # save the name of the pressed key to the current position
                self.current_keyboard_layout[key] = (self.row, self.column)
            self.next_key()

        hook = HookManager()
        hook.KeyDown = on_key_pressed
        hook.start()
        self.hook = hook

    def information(self):
        """
        print start information
        """
        print("The program will loop through each device and trough every key.")
        print("Please press the green lit key. If no Key is lit press 'escape'")
        print("The result can be inserted to to a copy of 'layout.py' which can replace the old file")

    def finish(self):
        """
        stop thread and print results to console and file
        """
        self.hook.cancel()
        with open("layout.py", "w") as f:
            f.write("layouts = ")
            pprint(self.all_layouts, f, sort_dicts=False)
        print("All keyboards are done")
        print("Layouts have been updated in 'layout.py'. Move the file to the package install position "
              "(e.g. {~/.local|/usr}/lib/python3.x/site-packages/i3razer)"
              "and consider opening a pull request on github")
        exit()

if __name__ == "__main__":
    map_layout()
