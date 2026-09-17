"""SIGKILL a real lifecycle operation in a disposable Fedora fixture only."""
import os
from pathlib import Path
import signal
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import omadora

operation = sys.argv[1]
original = omadora.run


def interrupted(*args, **kwargs):
    if (operation == 'install' and str(args[0]) == 'fc-cache') or (
            operation == 'upgrade' and str(args[0]) == 'Hyprland' and '--verify-config' in args):
        os.kill(os.getpid(), signal.SIGKILL)
    return original(*args, **kwargs)


omadora.run = interrupted
sys.argv = ['omadora.py', operation] + (['--local'] if operation == 'upgrade' else [])
omadora.main()
