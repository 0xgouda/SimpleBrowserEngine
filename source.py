import socket
import ssl
import time
import gzip
import tkinter

class URL:
    def __init__(self, url, redirect_count=0):
        # checks if view-source scheme is in use
        self.scheme, url = url.split(":", 1)
        assert self.scheme in ["http", "https", "file", "data", "view-source"]
        self.view_source = False
        if self.scheme == "view-source":
            self.view_source = True
            self.scheme, url = url.split("://", 1)
        
        # save the number of redirects
        self.redirect_count = redirect_count

        # initialize the cache dictionary
        self.cache = {}

        # no socket connections exist
        self.s = None
        self.connection = None

        # check if data scheme is in use
        if self.scheme == "data":
            self.mediatype, self.data = url.split(",", 1)
            return
        
        # reassing the scheme that existed after view-source
        if self.view_source == False:
            url = url.split("//", 1)[1]

        # if file won't go further with http stuff
        if self.scheme == "file":
            self.host = url
            return

        # assigns the host and path to variables
        if "/" not in url:
            url = url + "/"
        self.host, url = url.split("/", 1)
        self.path = "/" + url

        # set the port 
        if self.scheme == "http":
            self.port = 80
        elif self.scheme == "https":
            self.port = 443

        # handle custom ports
        if ":" in self.host:
            self.host, port = self.host.split(":", 1)
            self.port = int(port)
    
    # creates the connection socket
    def create_socket(self):
        # save the current connection's host
        self.connection = self.host

        # create a socket and establish the connection
        s = socket.socket(
            family = socket.AF_INET,
            type = socket.SOCK_STREAM,
            proto = socket.IPPROTO_TCP
        )
        s.connect((self.host, self.port))
        
        # create the ssl context socket 
        if self.scheme == "https":
            ctx = ssl.create_default_context()
            s = ctx.wrap_socket(s, server_hostname=self.host)
        
        return s

    # handles redirection
    def redirect(self, response_headers):
        if self.redirect_count > 5:
                return "Error due to too much redirects"
        self.redirect_count += 1

        location = response_headers["location"]
        if location[0] == "/":
            self.path = location
        else:
            self.__init__(location, self.redirect_count)
        return self.request()

    # caching responses
    def cache_reponse(self, key, status_line, content, reponse_headers):
        if status_line.split(" ", 2)[1] == "200":
            maxage = 3600
            if "cache-control" in reponse_headers:
                cache_control = reponse_headers["cache-control"].strip().lower()
                if ',' not in cache_control:
                    if 'no-store' in cache_control:
                        return
                    elif 'max-age=' in cache_control:
                        try:
                            maxage = int(cache_control.split("=", 1)[1])
                        except ValueError:
                            maxage = 3600
                
            expiration_date = time.time() + maxage
            self.cache[key] = [status_line, content, reponse_headers, expiration_date]

    # retrieve cached reponses
    def get_cached_response(self, key):
        if key in self.cache:
            cached_content = self.cache[key]
            expiration_date = cached_content[3]
            if time.time() <= expiration_date:
                return cached_content[:3]
            else:
                del self.cache[key]
        return None

    # sends the request and receives the response
    def request(self):
        key = self.scheme + "://" + self.host + self.path
        cached = self.get_cached_response(key)
        if cached == None:
            if self.s is None or self.connection != self.host:
                self.s = self.create_socket()

            # sends the request
            request = "GET {} HTTP/1.1\r\n".format(self.path)
            request += "Host: {}\r\n".format(self.host)
            request += "User-Agent: the browser of gouda\r\n"
            request += "Accept-Encoding: gzip\r\n"
            request += "\r\n"
            self.s.send(request.encode("utf8"))

            # receiving the response
            response = self.s.makefile("rb")
            
            # assigning reponse headers to variables
            statusline = response.readline().decode("utf-8")
            version, status, explanation = statusline.split(" ", 2)
            
            response_headers = {}
            while True:
                line = response.readline().decode("utf-8")
                if line == "\r\n": break
                header, value = line.split(":", 1)
                response_headers[header.casefold()] = value.strip()

            # gathers the data if sent chunked
            if "transfer-encoding" in response_headers:
                chunks = []
                while True:
                    chunk_size_hex = response.readline().decode("utf-8").strip()
                    if chunk_size_hex == '':
                        break
                    chunk_size = int(chunk_size_hex, 16)
                    chunks.append(response.read(chunk_size))
                
                response = bytearray()
                for data in chunks:
                    response += data
            else:
                response = response.read()

            # decodes the data if gzip encoded
            if "content-encoding" in response_headers:
                 content = gzip.decompress(response).decode("utf-8")
            else:
                 content = response.read().decode("utf-8")

            # Caching the response
            self.cache_reponse(key, statusline, content, response_headers)
        else:
            version, status, explanation = cached[0].split(" ", 2)
            content = cached[1]
            response_headers = cached[2]

        # handle redirects
        status = int(status)
        if status >= 300 and status < 400:
            return self.redirect(response_headers)
        else:
            # returning the body
            return content

    # closes the socket connection
    def close(self):
        if self.s:
            self.s.close()
            self.s = None

    # open local files
    def open_file(self):
        file = open(self.host, 'r')
        return file.read()

# global dimension varibales 
WIDTH, HEIGHT = 800, 600
HSTEP, VSTEP = 13, 18
SCROLL_STEP = 100

# saves all the page text to a list
def layout(text):
    display_list = []
    cursor_x, cursor_y = HSTEP, VSTEP
    for c in text:
        display_list.append((cursor_x, cursor_y, c))
        cursor_x += HSTEP
        if cursor_x >= WIDTH - HSTEP:
            cursor_y += VSTEP
            cursor_x = HSTEP

    return display_list

class Browser:
    def __init__(self):
        # creates a windows and attaches it to a canvas
        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(
            self.window,
            width = WIDTH,
            height = HEIGHT
        )
        self.canvas.pack()

        # saves the scrolled distance for later user
        self.scroll = 0

        # attaches the down arrow key with a method to be called when entered
        self.window.bind("<Down>", self.scrolldown)
    
    # increases the scroll distance and redraws based on it
    def scrolldown(self, e):
        self.scroll += SCROLL_STEP
        self.draw()

    def load(self, url):
        # determine type of action based on scheme
        if url.scheme == "file":
            body = url.open_file()
        elif url.scheme in ["http", "https", "view-source"]:
            body = url.request()
        elif url.scheme == "data": 
            body = url.data

        # view source required or not
        if url.view_source == False:
            text = lex(body)
        else: 
            text = body
        
        # displays the the text
        self.display_list = layout(text)
        self.draw()

    def draw(self):
        self.canvas.delete("all")
        for x, y, c in self.display_list:
            # excludes the chars under the viewport
            if y > self.scroll + HEIGHT: continue
            # excludes the chars above the viewport
            if y + VSTEP < self.scroll: continue
            self.canvas.create_text(x, y - self.scroll, text=c)

# filters tags<>
def lex(body):
    in_tag = False
    text = ""
    for c in body:
        if c == "<":
            in_tag = True
        elif c == ">":
            in_tag = False
        elif not in_tag:   
            text += c

    text.replace("&lt;", "<").replace("&gt;", ">")

    return text
    
if __name__ == "__main__":
    import sys
    
    try:
        url = sys.argv[1]
    except IndexError:
        url = "https://example.org"
    
    Browser().load(URL(url))
    tkinter.mainloop()