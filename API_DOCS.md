# Brother QL Label Printer API Documentation

This service provides a queue-based API for printing labels on Brother QL label printers.

## Print Queue

Labels are printed by submitting print jobs to a queue. The service processes jobs from the queue in FIFO order.

### Job Format

Print jobs should be submitted to the `label_print_jobs` queue in Supabase with the following format:

```json
{
  "image": "base64_encoded_image_data",
  "label_size": "62",  // optional, defaults to config default size
  "threshold": 70,     // optional, defaults to 70
  "rotate": "auto"     // optional, defaults to "auto"
}
```

### Parameters

- `image`: Required. Base64 encoded image data. Supports PNG, JPEG, and BMP formats. Images will be converted to bitmap for printing.
- `label_size`: Optional. The label size to print on. Defaults to the configured default size. Available sizes:
  - "12": 12mm continuous
  - "29": 29mm continuous
  - "38": 38mm continuous
  - "50": 50mm continuous
  - "54": 54mm x 29mm die-cut
  - "62": 62mm continuous
  - "62red": 62mm continuous (black/red)
  - More sizes available, check printer documentation
- `threshold`: Optional. Threshold for converting color/grayscale images to black and white. Value between 0-255, defaults to 70.
- `rotate`: Optional. Image rotation. Values:
  - "auto": Automatically determine best rotation (default)
  - 0: No rotation
  - 90: Rotate 90 degrees clockwise
  - 180: Rotate 180 degrees
  - 270: Rotate 270 degrees clockwise

### Example

Here's an example of submitting a print job using the Supabase client:

```javascript
const { data, error } = await supabase
  .schema('pgmq_public')
  .rpc('send', {
    queue_name: 'label_print_jobs',
    message: {
      image: 'base64_encoded_image_data',
      label_size: '62',
      threshold: 70,
      rotate: 'auto'
    }
  });
```

## Error Handling

The service will log errors that occur during print job processing. Failed jobs are currently discarded, but the error will be logged with details about what went wrong.

Common errors:
- Invalid base64 image data
- Unsupported image format
- Invalid label size
- Printer communication errors 