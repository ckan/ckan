import os
import sys

import ckanserviceprovider.web as web
web.init()

import datapusher.jobs as jobs

application = web.app
