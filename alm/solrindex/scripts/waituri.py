
"""This is a script to wait for a URI to be available.

Use it to wait for Solr to start up.
"""

from urllib2 import urlopen
import sys
import time

timeout = 60

def main():
    uri = sys.argv[1]
    stop_at = time.time() + timeout
    out = sys.stdout
    out.write("Waiting for %s." % uri)
    out.flush()
    try:
        while time.time() < stop_at:
            try:
                f = urlopen(uri)
                f.read()
            except (KeyboardInterrupt, SystemExit):
                raise
            except:
                out.write(".")
                out.flush()
                time.sleep(1)
            else:
                f.close()
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
