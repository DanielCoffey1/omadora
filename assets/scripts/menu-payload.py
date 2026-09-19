"""Encode selector/input IPC using the Python runtime already required by Omadora."""
import json
import sys

mode, prompt, selection_file, done_file, width, height, *options = sys.argv[1:]
payload = {'mode': mode, 'prompt': prompt, 'selectionFile': selection_file,
           'doneFile': done_file}
if mode == 'select':
    payload['options'] = options
if width:
    payload['width'] = int(width)
if height:
    payload['maxHeight'] = int(height)
print(json.dumps(payload, ensure_ascii=False))
