"""Disposable GTK target for real universal copy/cut/paste key tests."""
from pathlib import Path
import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

window = Gtk.Window(title='Omadora clipboard fixture')
window.set_default_size(640, 180)
entry = Gtk.Entry()
entry.set_text('Omadora copy from GTK')
entry.connect('changed', lambda widget: Path('/tmp/omadora-entry.txt').write_text(widget.get_text()))
window.add(entry)
window.connect('destroy', Gtk.main_quit)
window.show_all()
entry.grab_focus()
Gtk.main()
