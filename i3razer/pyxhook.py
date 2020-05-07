# Heavily based on [pyxhook](https://github.com/JeffHoogland/pyxhook)
# Thanks to all people working on it
# I modified it for simpler usage


# One could use the module keyboard, but this requires root to read the keys
# It also needs nome API to use for this case

import logging
import re
import sys
import threading
import time

from Xlib import X, XK, display
from Xlib.ext import record
from Xlib.protocol import rq


class HookManager(threading.Thread):
    """ This is the main class. Instantiate it, and you can hand it KeyDown
        and KeyUp (functions in your own code) which execute to parse the
        pyxhookkeyevent class that is returned.

        This simply takes these two values for now:
        KeyDown : The function to execute when a key is pressed, if it
                  returns anything. It hands the function an argument that
                  is the pyxhookkeyevent class.
        KeyUp   : The function to execute when a key is released, if it
                  returns anything. It hands the function an argument that is
                  the pyxhookkeyevent class.
    """

    def __init__(self, parameters=False):
        threading.Thread.__init__(self)
        self.finished = threading.Event()

        # Give these some initial values
        self.mouse_position_x = 0
        self.mouse_position_y = 0

        # Compile our regex statements.
        self.logrelease = re.compile('.*')
        self.isspace = re.compile('^space$')
        # Choose which type of function use
        self.parameters = parameters
        if parameters:
            self.lambda_function = lambda x, y: True
        else:
            self.lambda_function = lambda x: True
        # Assign default function actions (do nothing).
        self.KeyDown = self.lambda_function
        self.KeyUp = self.lambda_function
        self.MouseButtonDown = self.lambda_function
        self.MouseButtonUp = self.lambda_function
        self.MouseMovement = self.lambda_function

        self.contextEventMask = [X.KeyPress, X.MotionNotify]

        # Hook to our display.
        self.local_dpy = display.Display()
        self.record_dpy = display.Display()
        self.context = None  # Context initialized in run

    def run(self):
        # Check if the extension is present
        if not self.record_dpy.has_extension("RECORD"):
            logging.critical("RECORD extension not found")
            sys.exit(1)
        # r = self.record_dpy.record_get_version(0, 0)

        # Create a recording context; we only want key and mouse events
        self.context = self.record_dpy.record_create_context(
            0,
            [record.AllClients],
            [{
                'core_requests':    (0, 0),
                'core_replies':     (0, 0),
                'ext_requests':     (0, 0, 0, 0),
                'ext_replies':      (0, 0, 0, 0),
                'delivered_events': (0, 0),
                #                (X.KeyPress, X.ButtonPress),
                'device_events':    tuple(self.contextEventMask),
                'errors':           (0, 0),
                'client_started':   False,
                'client_died':      False,
            }])

        # Enable the context; this only returns after a call to
        # record_disable_context, while calling the callback function in the
        # meantime
        self.record_dpy.record_enable_context(self.context, self._process_events)
        # Finally free the context
        self.record_dpy.record_free_context(self.context)

    def cancel(self):
        self.finished.set()
        self.local_dpy.record_disable_context(self.context)
        self.local_dpy.flush()

    @staticmethod
    def print_event(event):
        print(event)
        print()

    def _process_events(self, reply):
        if reply.category != record.FromServer:
            return
        if reply.client_swapped:
            logging.warning("* received swapped protocol data, cowardly ignored")
            return
        int_val = reply.data[0]
        if (not reply.data) or (int_val < 2):
            # not an event
            return
        data = reply.data
        while len(data):
            event, data = rq.EventField(None).parse_binary_value(
                data,
                self.record_dpy.display,
                None,
                None
            )
            if event.type == X.KeyPress:
                hook_event = self._key_press_event(event)
                self.KeyDown(hook_event)
            elif event.type == X.KeyRelease:
                hook_event = self._key_release_event(event)
                self.KeyUp(hook_event)
            # Only Keyboard events, ignore mouse

            # elif event.type == X.ButtonPress:
            #     hook_event = self._button_press_event(event)
            #     self.MouseAllButtonsDown(hook_event)
            # elif event.type == X.ButtonRelease:
            #     hook_event = self._button_release_event(event)
            #     self.MouseAllButtonsUp(hook_event)
            # elif event.type == X.MotionNotify:
            # # use mouse moves to record mouse position, since press and
            # # release events do not give mouse position info
            # # (event.root_x and event.root_y have bogus info).
            # hook_event = self._mouse_move_event(event)
            # self.MouseMovement(hook_event)

    def _key_press_event(self, event):
        # Always take the first keysym, shift is not handled
        # Shift will make a different key released, if press is without shift
        keysym = self.local_dpy.keycode_to_keysym(event.detail, 0)
        return self._make_key_hook_event(keysym, event)

    def _key_release_event(self, event):
        # Always take the first keysym, shift is not handled
        # Shift will make a different key released, if press is without shift
        keysym = self.local_dpy.keycode_to_keysym(event.detail, 0)
        return self._make_key_hook_event(keysym, event)

    def _button_press_event(self, event):
        return self._make_mouse_hook_event(event)

    def _button_release_event(self, event):
        return self._make_mouse_hook_event(event)

    def _mouse_move_event(self, event):
        self.mouse_position_x = event.root_x
        self.mouse_position_y = event.root_y
        return self._make_mouse_hook_event(event)

    _keysym_names = {}  # fast access to keysym name

    def reset_keysyms(self):
        self._keysym_names = {}

    # need the following because XK.keysym_to_string() only does printable
    # chars rather than being the correct inverse of XK.string_to_keysym()
    def lookup_keyname(self, keysym):
        # save keysym names internal for faster access (it is called on every key event, should be fast)
        if keysym in self._keysym_names:
            return self._keysym_names[keysym]
        keyname = ""
        for name in dir(XK):
            if name.startswith("XK_") and getattr(XK, name) == keysym:
                keyname = name.lstrip("XK_")
                break
        if not keyname:
            keyname = f"[{keysym}]"
        self._keysym_names[keysym] = keyname
        return keyname

    def ascii_value(self, keysym):
        asciinum = XK.string_to_keysym(self.lookup_keyname(keysym))
        return asciinum % 256

    def _make_key_hook_event(self, keysym, event):
        window = self._xwindow_info()
        if event.type == X.KeyPress:
            message_name = "key down"
        elif event.type == X.KeyRelease:
            message_name = "key up"
        else:
            message_name = ""
        return PyxhookKeyEvent(
            window["handle"],
            window["name"],
            window["class"],
            self.lookup_keyname(keysym),
            self.ascii_value(keysym),
            False,
            event.detail,
            message_name
        )

    def _make_mouse_hook_event(self, event):
        window = self._xwindow_info()
        if event.detail == 1:
            message_name = "mouse left "
        elif event.detail == 3:
            message_name = "mouse right "
        elif event.detail == 2:
            message_name = "mouse middle "
        elif event.detail == 5:
            message_name = "mouse wheel down "
        elif event.detail == 4:
            message_name = "mouse wheel up "
        else:
            message_name = f"mouse {event.detail} "

        if event.type == X.ButtonPress:
            message_name = f"{message_name} down"
        elif event.type == X.ButtonRelease:
            message_name = f"{message_name} up"
        else:
            message_name = "mouse moved"
        return PyxhookMouseEvent(
            window["handle"],
            window["name"],
            window["class"],
            (self.mouse_position_x, self.mouse_position_y),
            message_name
        )

    def _xwindow_info(self):
        try:
            windowvar = self.local_dpy.get_input_focus().focus
            wmname = windowvar.get_wm_name()
            wmclass = windowvar.get_wm_class()
            wmhandle = str(windowvar)[20:30]
        except:
            # This is to keep things running smoothly.
            # It almost never happens, but still...
            return {"name": None, "class": None, "handle": None}
        if (wmname is None) and (wmclass is None):
            try:
                windowvar = windowvar.query_tree().parent
                wmname = windowvar.get_wm_name()
                wmclass = windowvar.get_wm_class()
                wmhandle = str(windowvar)[20:30]
            except:
                # This is to keep things running smoothly.
                # It almost never happens, but still...
                return {"name": None, "class": None, "handle": None}
        if wmclass is None:
            return {"name": wmname, "class": wmclass, "handle": wmhandle}
        else:
            return {"name": wmname, "class": wmclass[0], "handle": wmhandle}


class PyxhookKeyEvent:
    """ This is the class that is returned with each key event.f
        It simply creates the variables below in the class.

        Window         : The handle of the window.
        WindowName     : The name of the window.
        WindowProcName : The backend process for the window.
        Key            : The key pressed, shifted to the correct caps value.
        Ascii          : An ascii representation of the key. It returns 0 if
                         the ascii value is not between 31 and 256.
        KeyID          : This is just False for now. Under windows, it is the
                         Virtual Key Code, but that's a windows-only thing.
        ScanCode       : Please don't use this. It differs for pretty much
                         every type of keyboard. X11 abstracts this
                         information anyway.
        MessageName    : "key down", "key up".
    """

    def __init__(self, window, window_name, window_proc_name, key, ascii_value, key_id, scan_code, message_name):
        self.Window = window
        self.WindowName = window_name
        self.WindowProcName = window_proc_name
        self.Key = key
        self.Ascii = ascii_value
        self.KeyID = key_id
        self.ScanCode = scan_code
        self.MessageName = message_name

    def __str__(self):
        return '\n'.join((
            'Window Handle: {s.Window}',
            'Window Name: {s.WindowName}',
            'Window\'s Process Name: {s.WindowProcName}',
            'Key Pressed: {s.Key}',
            'Ascii Value: {s.Ascii}',
            'KeyID: {s.KeyID}',
            'ScanCode: {s.ScanCode}',
            'MessageName: {s.MessageName}',
        )).format(s=self)


class PyxhookMouseEvent:
    """This is the class that is returned with each key event.f
    It simply creates the variables below in the class.

        Window         : The handle of the window.
        WindowName     : The name of the window.
        WindowProcName : The backend process for the window.
        Position       : 2-tuple (x,y) coordinates of the mouse click.
        MessageName    : "mouse left|right|middle down",
                         "mouse left|right|middle up".
    """

    def __init__(self, window, window_name, window_proc_name, position, message_name):
        self.Window = window
        self.WindowName = window_name
        self.WindowProcName = window_proc_name
        self.Position = position
        self.MessageName = message_name

    def __str__(self):
        return '\n'.join((
            'Window Handle: {s.Window}',
            'Window\'s Process Name: {s.WindowProcName}',
            'Position: {s.Position}',
            'MessageName: {s.MessageName}',
        )).format(s=self)


if __name__ == '__main__':
    hm = HookManager()
    hm.KeyDown = hm.print_event
    hm.KeyUp = hm.print_event
    hm.MouseButtonDown = hm.print_event
    hm.MouseButtonUp = hm.print_event
    hm.start()
    time.sleep(10)
    hm.cancel()
