#!/usr/bin/python3

from flup.server.fcgi import WSGIServer
from wsgi import application

WSGIServer(application).run()
