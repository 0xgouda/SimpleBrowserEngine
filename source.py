import sys
import tkinter
import browser
from url import URL

if __name__ == "__main__":
    if '-h' in sys.argv or '--help' in sys.argv:
        print('-h or --help: show help menu\nusage:  python3 main.py http[s]://example.org\n\tpython3 source.py file://path/to/your/file\n\tpython3 source.py data:text/html,"gouda 3mk"\n\tpython3 source.py view-source:http[s]://example.org')
        exit()
    try:
        url = sys.argv[1]
    except:
        print('-h or --help: show help menu\nusage:  python3 main.py http[s]://example.org\n\tpython3 source.py file://path/to/your/file\n\tpython3 source.py data:text/html,"gouda 3mk"\n\tpython3 source.py view-source:http[s]://example.org')
        exit()

    browser.Browser().load(URL(url))
    tkinter.mainloop()