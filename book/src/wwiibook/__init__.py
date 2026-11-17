"""Print books from the WWII research kit's records.

A book is a Typst file. Its pages ask for what they need (an archive page by its citation, a table of records, a QR
tag) through the functions in the `wwii-book` Typst package; each request draws a placeholder until it is prepared.
`build()` asks Typst for the requests, prepares each one (fetching and cropping scans, staging records as JSON,
drawing QR codes) into the book's `build/` folder, and compiles again with everything in place.
"""
from .build import build
from .cite import Cite, parse

__all__ = ["Cite", "build", "parse"]
__version__ = "0.1.0"
