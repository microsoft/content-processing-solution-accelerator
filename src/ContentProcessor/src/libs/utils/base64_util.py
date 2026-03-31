# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Base-64 encoding detection utility.

Used by the pipeline queue handler to decide whether incoming queue
messages need decoding before JSON deserialization.
"""

import base64


def is_base64_encoded(data: str) -> bool:
    """Return True if *data* is a valid base-64 encoded string.

    Attempts a round-trip decode/encode and checks for equality.
    """
    try:
        # Try to decode the string
        decoded_data = base64.b64decode(data, validate=True)
        # Check if the decoded data can be encoded back to the original string
        if base64.b64encode(decoded_data).decode("utf-8") == data:
            return True
        return False
    except Exception:
        return False
