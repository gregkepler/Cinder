# =============================================================================================== Logging

class Logger(object):
    
    def log(self, message, level=0):
        if level == 0 or not level:
            message_prefix = "INFO"
        elif level == 1:
            message_prefix = "WARNING"
        elif level == 2:
            message_prefix = "ERROR"

        print("\r    *** " + message_prefix + ": [ " + message + " ] ***")

    def log_progress(message):
        sys.stdout.write('\r' + str(message))
        sys.stdout.write("\033[K")
        sys.stdout.flush()