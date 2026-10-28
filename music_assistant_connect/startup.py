"""Read Supervisor options as root, then drop privileges before serving Ingress."""
import json
import os
from pathlib import Path
import sys


def load_options(path=Path('/data/options.json')):
    """Read protected options before dropping privileges. Never log their contents."""
    config = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(config, dict):
        raise ValueError('Invalid app configuration')
    return config


def drop_privileges(user='pwuser'):
    import pwd
    account = pwd.getpwnam(user)
    # Fail closed if the image cannot switch to its unprivileged browser user.
    os.setgroups([])
    os.setgid(account.pw_gid)
    os.setuid(account.pw_uid)
    os.umask(0o077)
    if os.getuid() == 0 or os.getgid() == 0:
        raise RuntimeError('Refusing to serve as root')


def take_supervisor_token(environ=os.environ):
    """Move the Supervisor API token from the environment into memory."""
    token = environ.pop('SUPERVISOR_TOKEN', '')
    legacy = environ.pop('HASSIO_TOKEN', '')
    return token or legacy


def main():
    try:
        config = load_options()
        drop_privileges()
    except (OSError, ValueError, KeyError, RuntimeError):
        raise SystemExit('Appconfiguratie kon niet veilig worden geladen. Controleer de installatie en herstart de app.') from None
    # Keep the token only in Python memory, never in argv, environment, or a copy
    # on disk. Chromium and the HTTP server both run with the reduced identity.
    # The Supervisor token stays out of the environment Chromium and Xvfb inherit.
    supervisor_token = take_supervisor_token()
    sys.path.insert(0, str(Path(__file__).parent / 'app'))
    import main as application
    import supervisor
    import uvicorn
    application.APP_OPTIONS = config
    supervisor.TOKEN = supervisor_token
    uvicorn.run(application.app, host='0.0.0.0', port=8675,
                access_log=False, proxy_headers=False)


if __name__ == '__main__':
    main()
