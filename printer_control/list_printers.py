import win32print

def list_printers():
    printers = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)
    printer_names = [p[2] for p in printers]
    return printer_names

if __name__ == "__main__":
    names = list_printers()
    print("Available Printers:")
    for name in names:
        print(f"- {name}")
