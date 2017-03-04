
#!/usr/bin/env python3
# -*- coding: utf8 -*-

import sys
import signal

from smserver import conf
from smserver import server
from smserver import start_up

def main():
    start_up.start_up(*sys.argv[1:])

    serv = server.StepmaniaServer()

    try:
        signal.signal(signal.SIGTERM, lambda *_: sys.exit())
        signal.signal(signal.SIGHUP, lambda *_: serv.reload())
    except AttributeError:
        pass

    try:
        serv.start()
    except (KeyboardInterrupt, SystemExit):
        serv.stop()
        sys.exit()

if __name__ == "__main__":
    main()
