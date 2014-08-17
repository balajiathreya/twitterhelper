#!/usr/bin/python
import sys
import logging
logging.basicConfig(stream=sys.stderr)
sys.path.insert(0,"/var/www/twitterhelper/twitterhelper/")

from twitterhelper import app as application
