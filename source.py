import socket
import ssl
import time
import tkinter
import sys
import tkinter.font

# handles the url, connection, and returns the response
class URL:
    def __init__(self, url, redirect_count=0):
        # checks if view-source scheme is in use
        try:
            self.scheme, url = url.split(":", 1)
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
        except:
            self.scheme, self.path = "about", "blank"
    
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
                            maxage = 7200
                
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
            request += "\r\n"
            self.s.send(request.encode("utf8"))

            # receiving the response
            response = self.s.makefile("r", encoding="utf-8", newline="\r\n")
            
            # assigning reponse headers to variables
            statusline = response.readline()
            version, status, explanation = statusline.split(" ", 2)
            
            response_headers = {}
            while True:
                line = response.readline()
                if line == "\r\n": break
                header, value = line.split(":", 1)
                response_headers[header.casefold()] = value.strip()

            content = response.read(int(response_headers.get("content-length", 0)))

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

# caching the fonts to speed up text processing
FONTS = {}
def get_font(size, weight, style):
    key = (size, weight, style)
    if key not in FONTS:
        font = tkinter.font.Font(size=size, weight=weight, slant=style)
        # label object speeds the .measure() method
        label = tkinter.Label(font=font)
        FONTS[key] = (font, label)
    
    return FONTS[key][0]

# processes all the page text and saves it to a list
WIDTH, HEIGHT = 800, 600
HSTEP, VSTEP = 13, 18
class Layout:
    def __init__(self, tokens):
        self.display_list = []
        self.cursor_x = HSTEP
        self.cursor_y = VSTEP
        self.weight = "normal"
        self.style = "roman"
        self.size = 12
        self.line = []
        self.title = False

        # loops through each word to determine its shape
        for tok in tokens:
            self.token(tok)
        
        # final one for the incompelete line
        self.flush()
    
    def token(self, tok):
        if isinstance(tok, Text):
            for word in tok.text.split():
                self.word(word)
        elif tok.tag == "i":
            self.style = "italic"
        elif tok.tag == "/i":
            self.style = "roman"
        elif tok.tag == "b":
            self.weight = "bold"
        elif tok.tag == "/b":
            self.weight = "normal"
        elif tok.tag == "small":
            self.size -= 2
        elif tok.tag == "/small":
            self.size += 2
        elif tok.tag == "big":
            self.size += 4
        elif tok.tag == "/big":
            self.size -= 4
        elif tok.tag == "br":
            self.flush()
        elif tok.tag == "/p":
            self.flush()
            self.cursor_y += VSTEP   
        elif tok.tag == 'h1 class="title"':
            self.flush()
            self.title = True
            self.size += 4
            self.weight = "bold"
        elif tok.tag == "/h1" and self.title:
            self.flush()
            self.title = False
            self.size -= 2
            self.weight = "normal"
    
        return self.display_list

    # sets the metrics for the words in the line buffer
    def flush(self):
        if not self.line: return
        # calculates the baseline where all words should be on
        metrics = [font.metrics() for x, word, font in self.line]
        max_ascent = max([metric["ascent"] for metric in metrics])
        baseline = self.cursor_y + 1.25 * max_ascent

        # Centers the title
        measures = 0
        if self.title:
            measures = sum([font.measure(word) for x, word, font in self.line])

        # sets the y for each word to be 
        for x, word, font in self.line:
            y = baseline - font.metrics("ascent")
            self.display_list.append((((x + ((WIDTH - measures) / 2)) if self.title else x), y, word, font))

        max_descent = max([metric["descent"] for metric in metrics])
        self.cursor_y = baseline + 1.25 * max_descent
        self.cursor_x = HSTEP
        self.line = []


    # determines the shape and coordinates of the letter
    def word(self, word):
        font = get_font(self.size, self.weight, self.style)
        w = font.measure(word)

        if self.cursor_x + w > WIDTH - HSTEP:
            self.flush()
        else:
            self.line.append((self.cursor_x, word, font))
            self.cursor_x += w + font.measure(" ")
               
# Two classes to differentiate between Tags and Text
class Text:
    def __init__(self, text):
        self.text = text

class Tag:
    def __init__(self, tag):
        self.tag = tag

# distributes the body between Text and Tag objects
def lex(body, view_source):
    out = []

    # return all the source code
    if view_source: 
        for word in body.split():
            out.append(Text(word))
        return out

    # filter tags if view-source
    buffer = ""
    in_tag = False
    for c in body:
        if c == "<":
            in_tag = True
            if buffer: out.append(Text(buffer))
            buffer = ""
        elif c == ">":
            in_tag = False
            out.append(Tag(buffer))
            buffer = ""
        else: 
            buffer += c
            buffer = buffer.replace("&gt;", ">")
            buffer = buffer.replace("&lt;", "<")
            buffer = buffer.replace("&shy;", '\u00AD')
    
    if not in_tag and buffer:
        out.append(Text(buffer))

    return out

# initializes the real browser and handles its functions
SCROLL_STEP = 100
class Browser:
    def __init__(self):
        # creates a windows and attaches it to a canvas
        self.window = tkinter.Tk()
        self.title = "gouda space"
        self.canvas = tkinter.Canvas(
            self.window,
            width = WIDTH,
            height = HEIGHT
        )
        self.canvas.pack(fill=tkinter.BOTH, expand=True)

        # saves the scrolled distance for later user
        self.scroll = 0

        # attaches arrow keys and mouse wheel with methods to be called when triggered
        self.window.bind("<Down>", self.scrolldown)
        self.window.bind("<Up>", self.scrollup)
        self.window.bind("<MouseWheel>",self.on_mouse_wheel) # for windows/macos
        self.window.bind("<Button-4>", self.on_mouse_scroll) # linux scroll up
        self.window.bind("<Button-5>", self.on_mouse_scroll) # linux scroll down

        # call the resize method when and resizing happens
        self.window.bind("<Configure>", self.resize)

    # loads the response
    def load(self, url):
        # determine type of action based on scheme
        if url.scheme == "about" and url.path == "blank":
            body = "Please Enter a Correct URl"
        try:    
            if url.scheme == "file":
                body = url.open_file()
            elif url.scheme in ["http", "https", "view-source"]:
                body = url.request()
            elif url.scheme == "data": 
                body = url.data
        except:
            body = "Please Enter a Correct URL"
        
        # Filter the body from the tags
        self.text = lex(body, url.view_source)
        self.display_list = Layout(self.text).display_list
        # displays the the text
        self.draw()

    # resizes the screen
    def resize(self, e):
        global WIDTH, HEIGHT
        WIDTH, HEIGHT = e.width, e.height
        self.display_list = Layout(self.text).display_list
        self.draw()

    # methods to call when arrow keys or mouse wheel are triggered

    def on_mouse_wheel(self, e):
        if e.delta > 0:
            if self.scroll > 0:
                self.scroll -= SCROLL_STEP 
                self.draw()
        elif e.delta < 0:
            if self.scroll + HEIGHT < self.display_list[-1][1]:
                self.scroll += SCROLL_STEP
                self.draw()


    def on_mouse_scroll(self, e):
        if e.num == 4:
            if self.scroll > 0:
                self.scroll -= SCROLL_STEP 
                self.draw()
        elif e.num == 5:
            if self.scroll + HEIGHT < self.display_list[-1][1]:
                self.scroll += SCROLL_STEP
                self.draw()

    def scrollup(self, e):
        if self.scroll > 0:
            self.scroll -= SCROLL_STEP 
            self.draw()

    def scrolldown(self, e):
        if self.scroll + HEIGHT < self.display_list[-1][1]:
            self.scroll += SCROLL_STEP
            self.draw()


    def draw(self):
        self.canvas.delete("all")
        try:
            for x, y, word, font in self.display_list:
                # excludes the chars under and above the viewport
                if (y > self.scroll + HEIGHT or y + VSTEP < self.scroll): continue
            
                self.canvas.create_text(x, y - self.scroll, text=word, font=font, anchor="nw")

            total_height = self.display_list[-1][1] + VSTEP

            if total_height > HEIGHT:
                scrollbar_height = HEIGHT * (HEIGHT / total_height)
                scrollbar_y = HEIGHT * (self.scroll / total_height)

                self.canvas.create_rectangle(
                    WIDTH - 10,
                    scrollbar_y,
                    WIDTH,
                    scrollbar_y + scrollbar_height,
                    fill="#C0C0C0"
                )
        except:
            pass
    
if __name__ == "__main__":
    if '-h' in sys.argv or '--help' in sys.argv:
        print('\t-h or --help: show help menu\n\tusage: python3 source.py http[s]://example.org\n\tpython3 source.py file://path/to/your/file\n\tpython3 source.py data:text/html,"gouda 3mk"\n\tpython3 source.py view-source:http[s]://example.org')
        exit()
    try:
        url = sys.argv[1]
    except:
        print('\t-h or --help: show help menu\n\tusage: python3 source.py http[s]://example.org\n\tpython3 source.py file://path/to/your/file\n\tpython3 source.py data:text/html,"gouda 3mk"\n\tpython3 source.py view-source:http[s]://example.org')
        exit()
    Browser().load(URL(url))
    tkinter.mainloop()