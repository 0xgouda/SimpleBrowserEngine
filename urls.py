import socket
import ssl
import time

# handles the url parsing, connection creation, sending request and returns the response
class URL:
    MAX_REDIRECTS = 5

    def __init__(self, url, redirect_count=0):
        try:
            # future refactor: remove this to allow for captial query params data
            url = url.lower()

            self.view_source_enabled = False
            if url[:12] == "view-source:":            
                self.view_source_enabled = True
                url = url[12:]

            self.redirect_count = redirect_count
            self.cache = {}
            self.file = None

            self.scheme, url = url.split(":", 1)
            if self.scheme == "data":
                self.mediatype, self.data = url.split(",", 1)
                return
            url = url[2:]
            
            if self.scheme == "file":
                self.file_name = url
                return

            self.host, self.path = url.split("/", 1)
            self.path += "/" if self.path != "" else ""

            if self.scheme == "http":
                self.port = 80
            elif self.scheme == "https":
                self.port = 443

            if ":" in self.host:
                self.host, port = self.host.split(":", 1)
                self.port = int(port)
        except:
            self.scheme, self.path = "about", "blank"
    
    def create_socket(self):
        s = socket.socket(
            family = socket.AF_INET,
            type = socket.SOCK_STREAM,
            proto = socket.IPPROTO_TCP
        )
        s.connect((self.host, self.port))
        
        if self.scheme == "https":
            ctx = ssl.create_default_context()
            s = ctx.wrap_socket(s, server_hostname=self.host)
        
        return s

    def redirect(self, response_headers):
        if self.redirect_count > self.MAX_REDIRECTS:
                return "Error due to too much redirects"
        self.redirect_count += 1

        location = response_headers.get("location")
        if location[0] == "/":
            self.path = location
        else:
            self.__init__(location, self.redirect_count)
        return self.request()

    def cache_reponse(self, key, status_line, content, response_headers):
        if status_line.split(" ", 2)[1] == "200":
            if "cache-control" in response_headers:
                cache_control = response_headers["cache-control"].strip().lower()
                directives = cache_control.split(",")
                if 'no-store' in directives:
                    return

                if 'max-age=' in directives:
                    try:
                        max_age = int(cache_control.split("=", 1)[1])
                    except ValueError:
                        max_age = 7200
                
            expiration_date = time.time() + max_age
            self.cache[key] = {"status_line" : status_line, "content": content, "response_headers": response_headers, "expiration_date": expiration_date}

    def get_cached_response(self, key):
        if key not in self.cache:
            return None

        cached_response = self.cache[key]
        expiration_date = cached_response.get("content")
        if time.time() < expiration_date:
            return cached_response
        else:
            del self.cache[key]

    # TODO: handle socket closing logic
    def request(self):
        key = self.scheme + "://" + self.host + self.path
        cached_response = self.get_cached_response(key)
        if cached_response == None:
            socket = self.create_socket()

            request = f"GET {self.path} HTTP/1.1\r\n"
            request += f"Host: {self.host}\r\n"
            request += "User-Agent: gouda's browser\r\n"
            request += "\r\n"
            socket.send(request.encode("utf8"))

            response = socket.makefile("r", encoding="utf-8", newline="\r\n")
            
            statusline = response.readline()
            _, status_code, _ = statusline.split(" ", 2)
            
            response_headers = {}
            while True:
                line = response.readline()
                if line == "\r\n": break
                header, value = line.split(":", 1)
                response_headers[header.casefold()] = value.strip()

            content = response.read(int(response_headers.get("content-length", 0)))
            socket.close()

            self.cache_reponse(key, statusline, content, response_headers)
        else:
            content = cached_response["content"]
            _, status_code, _ = cached_response["status_line"].split(" ", 2)

        if int(status_code) >= 300 and int(status_code) < 400:
            return self.redirect(response_headers)
        else:
            return content

    def close(self):
        if self.file:
            self.file.close()
            self.file = None

    def open_file(self):
        self.file = open(self.file_name, 'r')
        return self.file.read()