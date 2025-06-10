#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This is a web service to print labels on Brother QL label printers.
"""

import sys, logging, random, json, argparse
from typing import Dict, Any

from bottle import run, route, get, post, response, request, redirect, static_file
from brother_ql.devicedependent import models, label_type_specs, label_sizes
from brother_ql.backends import backend_factory, guess_backend

from printer_service import LabelPrinterService

logger = logging.getLogger(__name__)

LABEL_SIZES = [(name, label_type_specs[name]['name']) for name in label_sizes]
printer_service = None

try:
    with open('config.json', encoding='utf-8') as fh:
        CONFIG = json.load(fh)
except FileNotFoundError as e:
    with open('config.example.json', encoding='utf-8') as fh:
        CONFIG = json.load(fh)

@route('/')
def index():
    redirect('/api')

@route('/static/<filename:path>')
def serve_static(filename):
    return static_file(filename, root='./static')

@route('/api')
def api_documentation():
    """Serve API documentation"""
    return static_file('API_DOCS.md', root='.')

@post('/api/print')
def print_label():
    """Print a label directly via HTTP request"""
    try:
        data = request.json

        if not data or 'image' not in data:
            response.status = 400
            return {'error': 'Image data is required'}

        # Extract parameters with defaults from config
        label_size = data.get('label_size', CONFIG['LABEL']['DEFAULT_SIZE'])
        threshold = data.get('threshold', 70)
        rotate = data.get('rotate', 'auto')

        # Print the label directly
        result = printer_service.print_label(
            image_data=data['image'],
            label_size=label_size,
            threshold=threshold,
            rotate=rotate
        )

        return {'success': True, 'message': 'Label printed successfully'}
    except Exception as e:
        logger.error(f"Error printing label: {e}")
        response.status = 500
        return {'error': str(e)}

def main():
    global DEBUG, BACKEND_CLASS, CONFIG, printer_service
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', default=False)
    parser.add_argument('--loglevel', type=lambda x: getattr(logging, x.upper()), default=False)
    parser.add_argument('--default-label-size', default=False, help='Label size inserted in your printer. Defaults to 62.')
    parser.add_argument('--model', default=False, choices=models, help='The model of your printer (default: QL-500)')
    parser.add_argument('--disable-printer-service', action='store_true', help='Disable the printer service')
    parser.add_argument('printer',  nargs='?', default=False, help='String descriptor for the printer to use (like tcp://192.168.0.23:9100 or file:///dev/usb/lp0)')
    args = parser.parse_args()

    if args.printer:
        CONFIG['PRINTER']['PRINTER'] = args.printer

    if args.port:
        PORT = args.port
    else:
        PORT = CONFIG['SERVER']['PORT']

    if args.loglevel:
        LOGLEVEL = args.loglevel
    else:
        LOGLEVEL = CONFIG['SERVER']['LOGLEVEL']

    if LOGLEVEL == 'DEBUG':
        DEBUG = True
    else:
        DEBUG = False

    if args.model:
        CONFIG['PRINTER']['MODEL'] = args.model

    if args.default_label_size:
        CONFIG['LABEL']['DEFAULT_SIZE'] = args.default_label_size

    logging.basicConfig(level=LOGLEVEL)

    try:
        selected_backend = guess_backend(CONFIG['PRINTER']['PRINTER'])
    except ValueError:
        parser.error("Couldn't guess the backend to use from the printer string descriptor")
    BACKEND_CLASS = backend_factory(selected_backend)['backend_class']

    print("available label sizes:")
    print(label_sizes)
    if CONFIG['LABEL']['DEFAULT_SIZE'] not in label_sizes:
        parser.error("Invalid --default-label-size. Please choose one of the following:\n:" + " ".join(label_sizes))
    print("using label size: " + CONFIG['LABEL']['DEFAULT_SIZE'])

    if not args.disable_printer_service:
        # Initialize label printer service
        printer_service = LabelPrinterService(CONFIG, BACKEND_CLASS)

    # Start web server
    run(
        host=CONFIG['SERVER']['HOST'],
        port=PORT,
        debug=DEBUG
    )

if __name__ == "__main__":
    main()
