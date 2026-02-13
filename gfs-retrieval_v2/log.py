import logging
import logging.handlers
import os
import sys
from contextlib import contextmanager
from io import StringIO
import os

# Get app name from command line arguments
APP_NAME = f"carl-gfs-data-retrieval.{os.path.basename(sys.argv[0].replace('.py', ''))}"

logger = logging.getLogger("carl-gfs-data-retrieval")
logger.setLevel(logging.DEBUG)

stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(process)d %(asctime)s - %(name)s - %(levelname)s - %(message)s')
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)

os.makedirs(os.path.dirname(f"./logs/{APP_NAME}.txt"), exist_ok=True)
file_handler = logging.FileHandler(f"./logs/{APP_NAME}.txt")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


@contextmanager
def log_to_stream():
	""" Copy the log to a stream for a with-clause """
	log = StringIO()
	stream_handler = logging.StreamHandler(stream=log)
	stream_handler.setLevel(logging.DEBUG)
	formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
	stream_handler.setFormatter(formatter)
	logger.addHandler(stream_handler)
	yield log
	logger.removeHandler(stream_handler)
