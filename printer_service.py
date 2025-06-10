import logging
from io import BytesIO
from typing import Dict, Any
from PIL import Image

from brother_ql.devicedependent import label_type_specs, ENDLESS_LABEL
from brother_ql import BrotherQLRaster, create_label

logger = logging.getLogger(__name__)


class LabelPrinterService:
    def __init__(self, model: str, printer_address: str, backend_class: Any):
        self.model = model
        self.printer_address = printer_address
        self.backend_class = backend_class

    def decode_base64_image(self, base64_string: str) -> Image.Image:
        """Decode a base64 string into a PIL Image"""
        import base64

        try:
            # Remove data URL prefix if present
            if "," in base64_string:
                base64_string = base64_string.split(",", 1)[1]

            # Decode base64 to bytes
            image_data = base64.b64decode(base64_string)

            # Create PIL Image from bytes
            image = Image.open(BytesIO(image_data))

            # Convert to RGB if necessary
            if image.mode not in ("L", "RGB"):
                image = image.convert("RGB")

            return image
        except Exception as e:
            logger.error(f"Failed to decode base64 image: {e}")
            raise

    def print_label(
        self,
        image_data: str,
        label_size: str,
        threshold: int = 70,
        rotate: str = "auto",
    ) -> bool:
        """
        Print a label directly from image data

        Args:
            image_data: Base64 encoded image data
            label_size: Size of label to print
            threshold: Threshold for black/white conversion
            rotate: Rotation setting ('auto', 0, 90, 180, 270)

        Returns:
            bool: True if successful
        """
        try:
            # Decode the image data
            image = self.decode_base64_image(image_data)

            # Determine if red is in the label size
            red = "red" in label_size

            # Create raster data
            qlr = BrotherQLRaster(self.model)

            # Create the label
            create_label(
                qlr,
                image,
                label_size,
                threshold=threshold,
                cut=True,
                rotate=rotate,
                red=red,
            )

            # Print the label
            be = self.backend_class(self.printer_address)
            be.write(qlr.data)
            be.dispose()

            logger.info(
                f"Label printed successfully (size: {label_size}, threshold: {threshold}, rotate: {rotate})"
            )
            return True

        except Exception as e:
            logger.error(f"Error printing label: {e}")
            raise
