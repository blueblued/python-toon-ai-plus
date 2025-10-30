"""
pytoon - Token-Oriented Object Notation for Python

A compact data format optimized for transmitting structured information to LLMs
with 30-60% fewer tokens than JSON.
"""

from .decoder import decode, ToonDecodeError
from .encoder import encode
from .types import Delimiter, DelimiterKey, DecodeOptions, EncodeOptions

__version__ = "0.1.1"
__all__ = [
    "encode",
    "decode",
    "ToonDecodeError",
    "Delimiter",
    "DelimiterKey",
    "EncodeOptions",
    "DecodeOptions",
]
