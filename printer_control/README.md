# TSC Printer Control via Python

This directory contains scripts to control the TSC DA200 printer using Python and the `win32print` library.

## Prerequisites
- Windows OS
- TSC Printer Driver installed (verified as "TSC DA200")
- Python `pywin32` library (`pip install pywin32`)

## Scripts

### `list_printers.py`
Lists all available local and network printers to verify the printer name.

### `tsc_printer.py`
Contains the `TSCPrinter` class and a test function.

**Usage:**
```python
from tsc_printer import TSCPrinter

printer = TSCPrinter("TSC DA200")

# Send raw TSPL commands
printer.send_command("SIZE 100 mm, 50 mm\r\nCLS\r\nTEXT 10,10,\"0\",0,1,1,\"Hello\"\r\nPRINT 1\r\n")

# Run a test print
printer.print_test_label()
```

## Configuration
Open `tsc_printer.py` and adjust the `SIZE` and `GAP` commands in `print_test_label` to match your actual label stock dimensions.
Default is 100mm x 50mm.

