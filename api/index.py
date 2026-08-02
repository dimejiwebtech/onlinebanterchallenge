import os
import sys

# Add project root directory to sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from config.wsgi import application

def handler(environ, start_response):
    path = environ.get('PATH_INFO', '/')
    # Clean Vercel function path prefix so Django routes URLs correctly
    if path.startswith('/api/index.py'):
        path = path[13:] or '/'
        environ['PATH_INFO'] = path
    return application(environ, start_response)

app = handler
