from policy import application
import logging
import logging.handlers
import socket

###Loggin to syslog:
class ContextFilter(logging.Filter):
  hostname = socket.gethostname()

  def filter(self, record):
    record.hostname = ContextFilter.hostname
    return True

f = ContextFilter()
application.logger.addFilter(f)
handler = logging.handlers.SysLogHandler('/dev/log')
formatter = logging.Formatter('%(asctime)s %(hostname)s POLICY SERVER:: %(message)s', datefmt='%b %d %H:%M:%S')
handler.setFormatter(formatter)
handler.setLevel(logging.INFO)
f = ContextFilter()
application.logger.addHandler(handler)

if __name__ == "__main__":
    application.run()
