from urllib.parse import urlparse, urljoin, parse_qs
import os
import requests

# handles the url parsing, connection creation, sending request and returns the response
class URL:
    SUPPORTED_DATA_SCHEME_FORMATS = ["text/html"]

    def __init__(self, url: str):
        self.view_source_enabled = False
        if url.startswith("view-source"):
            self.view_source_enabled = True     
            url = url[len('view-source:'):]
        
        self.opened_file = None

        parsed_url = urlparse(url)

        self.scheme = parsed_url.scheme
        self.path = parsed_url.path

        if self.scheme and parsed_url.netloc:
            self.url = urljoin(url, self.path)
            self.query_params = parse_qs(parsed_url.query)
        elif self.scheme == "file" and os.path.isfile(self.path):
            self.file_name = self.path
        elif self.scheme == "data" and ',' in self.path and any(self.path.split(',', 1)[0].startswith(fmt) for fmt in self.SUPPORTED_DATA_SCHEME_FORMATS):
            self.mediatype, self.data = self.path.split(',', 1)
        else:
            self.scheme, self.path = "about", "blank"

    def request(self):
        response = requests.get(self.url, params=self.query_params)
        return response.content.decode()

    def close_file(self):
        if self.opened_file:
            self.opened_file.close()
            self.opened_file = None

    def open_file(self):
        self.opened_file = open(self.file_name, 'r')
        return self.opened_file.read()