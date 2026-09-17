"""Check resolved GTK styling, not just the name stored in GSettings."""
import json
import sys

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk

Gtk.init([])
window = Gtk.Window()
window.realize()
color = window.get_style_context().get_background_color(Gtk.StateFlags.NORMAL)
settings = Gtk.Settings.get_default()
print(json.dumps({'display': Gdk.Display.get_default().__class__.__name__,
                  'theme': settings.get_property('gtk-theme-name'),
                  'background': [color.red, color.green, color.blue, color.alpha]}))
assert color.alpha > 0.9, 'GTK window background did not resolve'
if sys.argv[1] == 'dark':
    assert max(color.red, color.green, color.blue) < 0.5, 'GTK dark theme rendered light'
else:
    assert min(color.red, color.green, color.blue) > 0.5, 'GTK light theme rendered dark'
window.destroy()
