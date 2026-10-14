"""Python-network refusal for isolated T4 tests (installed as fixture sitecustomize)."""
import json
import os
from pathlib import Path
import sys

fixture = Path(os.environ['SAFE_HARBOR_T3_FIXTURE_ROOT']).resolve(strict=True)
log = Path(os.environ['SAFE_HARBOR_T4_NETWORK_LOG']).resolve(strict=False)
if fixture not in log.parents:
    raise RuntimeError('network refusal log outside fixture')


def _refuse_network(event, args):
    if event not in ('socket.getaddrinfo', 'socket.connect'):
        return
    destination = str(args[0] if event == 'socket.getaddrinfo' else args[1])
    row = json.dumps({'event': event, 'destination': destination}) + '\n'
    fd = os.open(log, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    try:
        os.write(fd, row.encode())
    finally:
        os.close(fd)
    raise RuntimeError('T4 isolated tests refuse Python network operations')


sys.addaudithook(_refuse_network)
# A child test can assert the hook loaded before its first project import.
sys._safe_harbor_t4_network_refused = True  # pylint: disable=protected-access
