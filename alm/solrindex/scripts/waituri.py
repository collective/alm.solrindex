
"""This is a script to wait for a URI to be available.

Use it to wait for Solr to start up.
"""

from urllib2 import urlopen
import sys
import time

default_timeout = 90


def main():
    if len(sys.argv) < 2:
        sys.exit('usage: %s URI [timeout]' % sys.argv[0])
    uri = sys.argv[1]
    if len(sys.argv) >= 3:
        timeout = int(sys.argv[2])
    else:
        timeout = default_timeout

    stop_at = time.time() + timeout
    out = sys.stdout
    out.write("Waiting for %s ." % uri)
    out.flush()
    try:
        while time.time() < stop_at:
            try:
                f = None
                try:
                    f = urlopen(uri)
                    f.read()
                finally:
                    if f is not None:
                        f.close()
            except (KeyboardInterrupt, SystemExit):
                raise
            except:
                out.write(".")
                out.flush()
                time.sleep(3)
            else:
                out.write(" Ok!\n")
                out.flush()
                return
        out.write(" Not responding.\n")
        out.flush()
        sys.exit(1)
    except (KeyboardInterrupt, SystemExit):
        sys.exit(1)

if __name__ == '__main__':
    main()
