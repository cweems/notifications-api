##!/usr/bin/env python
from __future__ import print_function

from flask import Flask
from app import create_app, version
from prometheus_flask_exporter import PrometheusMetrics

application = Flask('app')
create_app(application)
metrics = PrometheusMetrics(application, group_by='endpoint')
metrics.info('app_info', 'Application info', commit=version.__travis_commit__, time=version.__time__)
