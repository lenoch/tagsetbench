import logging


log = logging.getLogger('pythonConfig')  # exported
DEBUG = logging.DEBUG
INFO = logging.INFO
stream = None


def set_log_level(level):
    logging.root.setLevel(level)
    log.setLevel(level)
    if stream:
        stream.setLevel(level)


try:
    from colorlog import ColoredFormatter

    stream = logging.StreamHandler()
    formatter = ColoredFormatter('%(log_color)s%(message)s%(reset)s')
    stream.setFormatter(formatter)
    log.addHandler(stream)
    set_log_level(INFO)

    # barvičky ;-)
    # log.debug("A quirky message only developers care about")
    # log.info("Curious users might want to know this")
    # log.warn("Something is wrong and any user should be informed")
    # log.error("Serious stuff, this is red for a reason")
    # log.critical("OH NO everything is on fire")

except ImportError:
    ColoredFormatter = None
    logging.basicConfig(level=INFO, format='%(levelname)-8s %(message)s')
