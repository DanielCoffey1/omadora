"""Real rootless database queries and data retention in a disposable Fedora VM."""
import hashlib
import json
from pathlib import Path
import subprocess
import time
import pexpect

out = Path('/tmp/omadora-vm-results/databases')
out.mkdir(parents=True, exist_ok=True)
cli = ['python3', '/usr/local/share/omadora/omadora.py', 'app']
queries = {
    'postgres': ('psql -U postgres -c "CREATE TABLE IF NOT EXISTS omadora_test (value int); INSERT INTO omadora_test VALUES (42);"', 'psql -U postgres -tAc "SELECT value FROM omadora_test LIMIT 1"'),
    'mysql': ('mysql -uroot -p"$MYSQL_ROOT_PASSWORD" -e "CREATE DATABASE IF NOT EXISTS omadora_test; CREATE TABLE IF NOT EXISTS omadora_test.marker (value int); INSERT INTO omadora_test.marker VALUES (42);"', 'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" -Nse "SELECT value FROM omadora_test.marker LIMIT 1"'),
    'mariadb': ('mariadb -uroot -p"$MARIADB_ROOT_PASSWORD" -e "CREATE DATABASE IF NOT EXISTS omadora_test; CREATE TABLE IF NOT EXISTS omadora_test.marker (value int); INSERT INTO omadora_test.marker VALUES (42);"', 'mariadb -uroot -p"$MARIADB_ROOT_PASSWORD" -Nse "SELECT value FROM omadora_test.marker LIMIT 1"'),
    'redis': ('redis-cli SET omadora_test 42; redis-cli SAVE', 'redis-cli --raw GET omadora_test'),
    'mongodb': ('mongosh --quiet -u admin -p "$MONGO_INITDB_ROOT_PASSWORD" --authenticationDatabase admin --eval "db.getSiblingDB(\'omadora_test\').marker.insertOne({value:42})"', 'mongosh --quiet -u admin -p "$MONGO_INITDB_ROOT_PASSWORD" --authenticationDatabase admin --eval "db.getSiblingDB(\'omadora_test\').marker.findOne().value"'),
}
results = []


def transaction(action, key, log):
    child = pexpect.spawn(cli[0], cli[1:] + [action, key], encoding='utf-8', timeout=900)
    child.logfile_read = log
    while child.expect([r'\[[Yy]/[Nn]\]', r'\[[Nn]/[Yy]\]', pexpect.EOF]) != 2:
        child.sendline('y')
    child.close()
    assert child.exitstatus == 0, f'{action} {key} failed'


def query(name, command, expected=None):
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        result = subprocess.run(['podman', 'exec', name, 'sh', '-c', command], text=True, capture_output=True, timeout=30)
        if result.returncode == 0 and (expected is None or result.stdout.strip() == expected):
            return
        time.sleep(3)
    raise AssertionError('Database query did not succeed: ' + result.stderr[-1000:])


for db, (write, read) in queries.items():
    key, name = 'db-' + db, 'omadora-db-' + db
    record = {'database': db}
    with (out / (db + '.log')).open('w') as log:
        try:
            transaction('install', key, log)
            env = Path.home() / '.config/omadora/databases' / (db + '.env')
            assert env.stat().st_mode & 0o777 == 0o600
            digest = hashlib.sha256(env.read_bytes()).hexdigest()
            info = json.loads(subprocess.check_output(['podman', 'inspect', name]))[0]
            published = [binding for bindings in info['NetworkSettings']['Ports'].values() if bindings for binding in bindings]
            assert published and all(binding['HostIp'] == '127.0.0.1' for binding in published)
            query(name, write)
            query(name, read, '42')
            transaction('remove', key, log)
            assert subprocess.run(['podman', 'container', 'exists', name]).returncode == 1
            assert subprocess.run(['podman', 'volume', 'exists', name + '-data']).returncode == 0
            assert hashlib.sha256(env.read_bytes()).hexdigest() == digest
            transaction('install', key, log)
            query(name, read, '42')
            transaction('remove', key, log)
            record['status'] = 'PASS'
        except Exception as error:
            record.update(status='FAIL', error=str(error))
    results.append(record)
    (out / 'results.json').write_text(json.dumps(results, indent=2))
    print(json.dumps(record), flush=True)
assert all(r['status'] == 'PASS' for r in results), results
