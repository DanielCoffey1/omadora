# Anaconda Web UI boot-media launcher

`webui-desktop` is unmodified upstream source from
[rhinstaller/anaconda-webui, commit 02db271f369a9b100cd4038dd605514ff652d23c](https://github.com/rhinstaller/anaconda-webui/blob/02db271f369a9b100cd4038dd605514ff652d23c/webui-desktop).
It is licensed under LGPL-2.1-or-later; see the adjacent LICENSE.

Fedora 44's version 68 assumes the browser inherits a live desktop's display
and user session. This upstream revision also handles the standalone Anaconda
Wayland compositor on boot media. Omadora backports only the launcher into the
installer runtime; the installed desktop does not use this file. Remove this
backport once Fedora's packaged launcher includes these fixes and passes the
offline USB installation test.
