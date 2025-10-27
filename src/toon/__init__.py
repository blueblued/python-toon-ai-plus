"""
pytoon - Token-Oriented Object Notation for Python

A compact data format optimized for transmitting structured information to LLMs
with 30-60% fewer tokens than JSON.
"""

from .encoder import encode
from .types import Delimiter, DelimiterKey, EncodeOptions

__version__ = "0.1.0"
__all__ = ["encode", "Delimiter", "DelimiterKey", "EncodeOptions"]
