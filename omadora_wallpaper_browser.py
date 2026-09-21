"""Searchable GTK4 wallpaper previews; file and palette work stays off the UI thread."""
from concurrent.futures import ThreadPoolExecutor
import os
# Let GTK use the output's native scale instead of inheriting a forced terminal scale.
os.environ.pop('GDK_SCALE', None)
os.environ.pop('GDK_DPI_SCALE', None)
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gio, GLib


def run(library, mode='browse'):
    class Browser(Gtk.Application):
        def __init__(self):
            super().__init__(application_id='org.omadora.Wallpapers', flags=Gio.ApplicationFlags.NON_UNIQUE)
            self.pool = ThreadPoolExecutor(max_workers=1)
            self.busy = False
            self.chosen = None

        def do_activate(self):
            if self.get_active_window():
                self.get_active_window().present()
                return
            self.window = Gtk.ApplicationWindow(application=self, title='Omadora Wallpapers')
            self.window.set_default_size(1040, 740)
            self.window.connect('close-request', lambda *_: self.busy)
            outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
            for side in ('top', 'bottom', 'start', 'end'):
                getattr(outer, 'set_margin_' + side)(16)
            self.window.set_child(outer)
            bar = Gtk.Box(spacing=8)
            search = Gtk.SearchEntry(placeholder_text='Search wallpapers')
            search.set_hexpand(True)
            search.connect('search-changed', lambda *_: self.flow.invalidate_filter())
            bar.append(search)
            self.add_button = Gtk.Button(label='Add wallpapers')
            self.add_button.connect('clicked', lambda *_: self.add_dialog())
            bar.append(self.add_button)
            self.remove_button = Gtk.Button(label='Remove selected')
            self.remove_button.connect('clicked', lambda *_: self.remove_dialog())
            bar.append(self.remove_button)
            outer.append(bar)
            self.status = Gtk.Label(label='Click a wallpaper to apply its colors. Right-click to select it for removal.', xalign=0)
            self.status.set_wrap(True)
            outer.append(self.status)
            scroll = Gtk.ScrolledWindow(vexpand=True, hexpand=True)
            self.flow = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE, column_spacing=12, row_spacing=12,
                                    min_children_per_line=1, max_children_per_line=4, homogeneous=True)
            self.flow.set_filter_func(lambda child: search.get_text().casefold() in child.row['name'].casefold())
            scroll.set_child(self.flow); outer.append(scroll)
            self.rebuild()
            self.window.present()
            if mode == 'add-dialog': GLib.idle_add(self.add_dialog)
            if mode == 'remove-dialog': self.status.set_text('Click a wallpaper to remove it from your library.')

        def rebuild(self):
            child = self.flow.get_first_child()
            while child:
                following = child.get_next_sibling(); self.flow.remove(child); child = following
            selected = library.load().get('selected')
            for row in library.entries():
                tile = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
                picture = Gtk.Picture.new_for_filename(str(library.preview(row)))
                picture.set_size_request(220, 124)
                picture.set_can_shrink(True)
                tile.append(picture)
                label = Gtk.Label(label=('✓ ' if row['id'] == selected else '') + row['name'])
                label.set_ellipsize(3); label.set_max_width_chars(28); tile.append(label)
                button = Gtk.Button(child=tile, tooltip_text=row['name'])
                button.connect('clicked', lambda _button, r=row: self.choose(r))
                gesture = Gtk.GestureClick(button=3)
                gesture.connect('released', lambda _gesture, _n, _x, _y, r=row: self.select_remove(r))
                button.add_controller(gesture)
                child = Gtk.FlowBoxChild(child=button); child.row = row; self.flow.append(child)
            if not self.chosen:
                self.chosen = next((r for r in library.entries() if r['id'] == selected), None)

        def select_remove(self, row):
            self.chosen = row
            self.status.set_text('Selected for removal: ' + row['name'] + '. Use Remove selected.')

        def choose(self, row):
            if self.busy: return
            self.chosen = row
            if mode == 'remove-dialog': self.remove_dialog()
            else: self.work(lambda: library.apply(row['id']), 'Downloading if needed and generating colors for ' + row['name'] + '…', 'Applied ' + row['name'] + '. Some applications need reopening to update their colors.')

        def work(self, operation, message, success):
            if self.busy: return
            self.busy = True
            self.flow.set_sensitive(False); self.add_button.set_sensitive(False); self.remove_button.set_sensitive(False)
            self.status.set_text(message)
            future = self.pool.submit(operation)
            future.add_done_callback(lambda result: GLib.idle_add(self.finished, result, success))

        def finished(self, result, success):
            try:
                result.result(); self.status.set_text(success); self.rebuild()
            except BaseException as error:
                self.status.set_text('Could not complete the change: ' + str(error))
            self.busy = False
            self.flow.set_sensitive(True); self.add_button.set_sensitive(True); self.remove_button.set_sensitive(True)
            return False

        def add_dialog(self):
            if self.busy: return False
            dialog = Gtk.FileChooserNative(title='Add wallpapers', transient_for=self.window,
                                           action=Gtk.FileChooserAction.OPEN, accept_label='Add', cancel_label='Cancel')
            dialog.set_select_multiple(True)
            images = Gtk.FileFilter(name='Wallpapers (PNG, JPEG, WebP, GIF, BMP)')
            for ext in ('png', 'jpg', 'jpeg', 'webp', 'gif', 'bmp'): images.add_suffix(ext)
            dialog.add_filter(images)
            def response(chooser, result):
                if result == Gtk.ResponseType.ACCEPT:
                    files = chooser.get_files()
                    paths = [files.get_item(i).get_path() for i in range(files.get_n_items())]
                    self.work(lambda: [library.add(path) for path in paths], 'Adding wallpapers…', 'Wallpapers added. Click one to apply its colors.')
                chooser.destroy()
            dialog.connect('response', response); dialog.show()
            return False

        def remove_dialog(self):
            if self.busy: return
            if not self.chosen:
                self.status.set_text('Right-click a wallpaper to select it for removal.'); return
            row = self.chosen
            dialog = Gtk.MessageDialog(transient_for=self.window, modal=True, buttons=Gtk.ButtonsType.OK_CANCEL,
                                       text='Remove ' + row['name'] + '?', secondary_text='Removes it from this library. Your original imported file is kept. If it is active, another wallpaper will be applied first.')
            def response(prompt, answer):
                prompt.destroy()
                if answer == Gtk.ResponseType.OK:
                    self.chosen = None
                    self.work(lambda: library.remove(row['id']), 'Removing wallpaper…', 'Wallpaper removed from your library.')
            dialog.connect('response', response); dialog.present()

    app = Browser()
    try: return app.run([])
    finally: app.pool.shutdown(wait=False)
