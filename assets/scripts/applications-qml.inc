  // A fresh Gio process avoids delayed/missed DesktopEntries notifications.
  // Keep the last good list on failure and coalesce requests during a scan.
  property var freshApplications: null
  property bool applicationsPending: false

  function refreshApplications() {
    if (applicationScan.running) applicationsPending = true
    else applicationScan.running = true
  }

  IpcHandler {
    target: "omadora.apps"
    function refresh(): void { root.refreshApplications() }
  }

  Process {
    id: applicationScan
    command: ["python3", root.omarchyPath + "/../omadora_applications.py"]
    stdout: StdioCollector {}
    onExited: function(code) {
      if (code === 0) {
        try {
          var entries = JSON.parse(stdout.text)
          if (Array.isArray(entries)) {
            root.freshApplications = entries
            root.appsChanged()
          }
        } catch (e) { console.warn("Application refresh failed:", e) }
      }
      root.refreshIcons()
      if (root.applicationsPending) {
        root.applicationsPending = false
        Qt.callLater(root.refreshApplications)
      }
    }
  }

  Timer {
    id: applicationRefreshDelay
    interval: 150
    onTriggered: root.refreshApplications()
  }
