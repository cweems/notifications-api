##!/usr/bin/env python
from __future__ import print_function

from flask import Flask
from meinheld import server
import socket

from app import create_app

application = Flask('app')

create_app(application)

server.listen(("0.0.0.0", 8000))
server.run(application)
