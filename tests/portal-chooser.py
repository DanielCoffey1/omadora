"""Exercise the actual desktop portal and require its cancel response."""
import dbus
import dbus.mainloop.glib
from gi.repository import GLib

dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
bus = dbus.SessionBus()
loop = GLib.MainLoop()
result = []


def response(code, values):
    result.append(int(code))
    print('Portal response:', int(code), flush=True)
    loop.quit()


bus.add_signal_receiver(response, signal_name='Response', dbus_interface='org.freedesktop.portal.Request')
portal = dbus.Interface(bus.get_object('org.freedesktop.portal.Desktop', '/org/freedesktop/portal/desktop'),
                        'org.freedesktop.portal.FileChooser')
print(portal.OpenFile('', 'Omadora portal test', {'handle_token': dbus.String('omadora_test')}), flush=True)
GLib.timeout_add_seconds(60, lambda: loop.quit())
loop.run()
assert result == [1], result
