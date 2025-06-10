#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This is a web service to print labels on Brother QL label printers.
"""

import sys, logging, random, json, argparse
from typing import Dict, Any
import base64
from io import BytesIO

from bottle import run, route, get, post, response, request, static_file
from brother_ql.devicedependent import models
from brother_ql.backends import backend_factory, guess_backend
from jinja2 import Environment, FileSystemLoader
import os
from PIL import Image, ImageDraw

from printer_service import LabelPrinterService
from printer_manager import PrinterManager

logger = logging.getLogger(__name__)

printer_manager = None

# Setup Jinja2 template environment
template_dir = os.path.join(os.path.dirname(__file__), "views")
jinja_env = Environment(loader=FileSystemLoader(template_dir))


def generate_test_image(width=300, height=150):
    """Generate a simple test image with geometric shapes"""
    # Create a white background
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)

    # Draw some simple geometric shapes for testing
    # Black border
    draw.rectangle([0, 0, width - 1, height - 1], outline="black", width=2)

    # Diagonal lines
    draw.line([0, 0, width, height], fill="black", width=2)
    draw.line([width, 0, 0, height], fill="black", width=2)

    # Centered rectangle
    rect_width = width // 3
    rect_height = height // 3
    rect_x = (width - rect_width) // 2
    rect_y = (height - rect_height) // 2
    draw.rectangle(
        [rect_x, rect_y, rect_x + rect_width, rect_y + rect_height],
        outline="black",
        fill="lightgray",
        width=2,
    )

    # Four corner circles
    circle_radius = min(width, height) // 10
    positions = [
        (circle_radius, circle_radius),  # top-left
        (width - circle_radius, circle_radius),  # top-right
        (circle_radius, height - circle_radius),  # bottom-left
        (width - circle_radius, height - circle_radius),  # bottom-right
    ]

    for x, y in positions:
        draw.ellipse(
            [
                x - circle_radius,
                y - circle_radius,
                x + circle_radius,
                y + circle_radius,
            ],
            outline="black",
            fill="black",
        )

    return image


def image_to_base64(image):
    """Convert PIL Image to base64 string"""
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


@route("/")
def index():
    """Serve the printer management interface"""
    try:
        # Get available printers
        printers = printer_manager.list_printers() if printer_manager else []

        template = jinja_env.get_template("printer_management.jinja2")
        return template.render(
            website={
                "HTML_TITLE": "Printer Manager",
                "PAGE_TITLE": "Brother QL Printer Manager",
                "PAGE_HEADLINE": "Manage your printers",
            },
            printers=printers,
        )
    except Exception as e:
        logger.error(f"Error rendering printer management: {e}")
        return f"<h1>Error</h1><p>Failed to load printer management: {str(e)}</p>"


@route("/static/<filename:path>")
def serve_static(filename):
    return static_file(filename, root="./static")


@route("/api")
def api_documentation():
    """Serve API documentation"""
    return static_file("API_DOCS.md", root=".")


@post("/api/print")
def print_label():
    """Print a label directly via HTTP request"""
    try:
        data = request.json

        if not data or "image" not in data:
            response.status = 400
            return {"error": "Image data is required"}

        # Extract parameters with defaults from config
        label_size = data.get("label_size", "62")
        threshold = data.get("threshold", 70)
        rotate = data.get("rotate", "auto")
        printer_name = data.get("printer", None)

        # Get the printer service
        if printer_name:
            printer_service = printer_manager.get_printer_service(printer_name)
            if not printer_service:
                response.status = 400
                return {"error": f"Printer '{printer_name}' not found"}
        else:
            # Use default printer
            default_printer = printer_manager.get_default_printer()
            if not default_printer:
                response.status = 400
                return {"error": "No printers available"}
            printer_service = printer_manager.get_printer_service(default_printer)

        # Print the label directly
        result = printer_service.print_label(
            image_data=data["image"],
            label_size=label_size,
            threshold=threshold,
            rotate=rotate,
        )

        return {"success": True, "message": "Label printed successfully"}
    except Exception as e:
        logger.error(f"Error printing label: {e}")
        response.status = 500
        return {"error": str(e)}


@get("/api/printers")
def list_printers():
    """List all available printers"""
    try:
        printers = printer_manager.list_printers()
        return {"printers": printers}
    except Exception as e:
        logger.error(f"Error listing printers: {e}")
        response.status = 500
        return {"error": str(e)}


@post("/api/printers")
def add_printer():
    """Add a manual printer"""
    try:
        data = request.json

        if not data or "printer_id" not in data or "address" not in data:
            response.status = 400
            return {"error": "printer_id and address are required"}

        printer_id = data["printer_id"]
        address = data["address"]
        port = data.get("port", 9100)
        model = data.get("model", "QL-500")
        display_name = data.get("display_name")

        success = printer_manager.add_manual_printer(
            printer_id, address, port, model, display_name
        )

        if success:
            return {"success": True, "message": "Printer added successfully"}
        else:
            response.status = 400
            return {"error": "Failed to add printer"}

    except Exception as e:
        logger.error(f"Error adding printer: {e}")
        response.status = 500
        return {"error": str(e)}


@post("/api/printers/<printer_id>/display-name")
def set_printer_display_name(printer_id):
    """Set display name for a printer"""
    try:
        data = request.json

        if not data or "display_name" not in data:
            response.status = 400
            return {"error": "display_name is required"}

        display_name = data["display_name"]

        success = printer_manager.set_display_name(printer_id, display_name)

        if success:
            return {"success": True, "message": "Display name updated successfully"}
        else:
            response.status = 400
            return {"error": "Failed to update display name or printer not found"}

    except Exception as e:
        logger.error(f"Error setting display name: {e}")
        response.status = 500
        return {"error": str(e)}


@post("/api/printers/<printer_id>/remove")
def remove_printer(printer_id):
    """Remove a manually added printer"""
    try:
        success = printer_manager.remove_printer(printer_id)

        if success:
            return {"success": True, "message": "Printer removed successfully"}
        else:
            response.status = 400
            return {"error": "Failed to remove printer or printer not found"}

    except Exception as e:
        logger.error(f"Error removing printer: {e}")
        response.status = 500
        return {"error": str(e)}


@post("/api/printers/<printer_id>/test-print")
def test_print_printer(printer_id):
    """Print a test label on a specific printer"""
    try:
        # Get the printer display name
        display_name = None
        printers = printer_manager.list_printers()
        for printer in printers:
            if printer["printer_id"] == printer_id:
                display_name = printer["display_name"]
                break

        if not display_name:
            response.status = 404
            return {"error": f"Printer with ID '{printer_id}' not found"}

        # Get the printer service
        printer_service = printer_manager.get_printer_service(display_name)
        if not printer_service:
            response.status = 400
            return {"error": f"Could not connect to printer '{display_name}'"}

        # Generate test image
        test_image = generate_test_image()
        image_base64 = image_to_base64(test_image)

        # Print the test label
        result = printer_service.print_label(
            image_data=image_base64,
            label_size="62",  # Standard size
            threshold=70,
            rotate="auto",
        )

        return {
            "success": True,
            "message": f"Test label printed successfully on '{display_name}'",
        }
    except Exception as e:
        logger.error(f"Error printing test label: {e}")
        response.status = 500
        return {"error": str(e)}


def main():
    global DEBUG, BACKEND_CLASS, printer_manager
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", default=False)
    parser.add_argument(
        "--loglevel", type=lambda x: getattr(logging, x.upper()), default=False
    )

    parser.add_argument(
        "--model",
        default=False,
        choices=models,
        help="The model of your printer (default: QL-500)",
    )
    parser.add_argument(
        "--disable-printer-service",
        action="store_true",
        help="Disable the printer service",
    )
    parser.add_argument(
        "printer",
        nargs="?",
        default=False,
        help="String descriptor for the printer to use (like tcp://192.168.0.23:9100 or file:///dev/usb/lp0)",
    )
    args = parser.parse_args()

    if args.port:
        PORT = args.port
    else:
        PORT = 8013

    if args.loglevel:
        LOGLEVEL = args.loglevel
    else:
        LOGLEVEL = "WARNING"

    if LOGLEVEL == "DEBUG":
        DEBUG = True
    else:
        DEBUG = False

    logging.basicConfig(level=LOGLEVEL)

    BACKEND_CLASS = backend_factory("network")["backend_class"]

    if not args.disable_printer_service:
        # Initialize printer manager
        printer_manager = PrinterManager(BACKEND_CLASS)
        # Start discovery after initialization
        printer_manager.start_discovery()

    try:
        # Start web server
        run(host="0.0.0.0", port=PORT, debug=DEBUG)
    finally:
        # Clean shutdown
        if printer_manager:
            printer_manager.shutdown()


if __name__ == "__main__":
    main()
