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
            if not self.view_source:
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
    def __init__(self, tree, view_source):
        self.display_list = []
        self.cursor_x = HSTEP
        self.cursor_y = VSTEP
        self.weight = "normal"
        self.style = "roman"
        self.size = 12
        self.line = []
        self.title = False
        # self.view_source = view_source

        # initializes the loop over the nodes tree
        if view_source: self.view_source(tree)
        else: self.recurse(tree)
        
        # final one for the incompelete line
        self.flush()
    
    # handles the (bold, italic, ...etc) text formatting tags and the line breaks
    def open_tag(self, tag):
        if tag == "i":
            self.style = "italic"
        elif tag == "b":
            self.weight = "bold"
        elif tag == "small":
            self.size -= 2
        elif tag == "big":
            self.size += 4
        elif tag == "br":
            self.flush() 
        elif tag == "h1" and self.title:
            self.flush()
            self.size += 4
            self.weight = "bold"

    # reverts the changes made by open_tag
    def close_tag(self, tag):
        if tag == "i":
            self.style = "roman"
        elif tag == "b":
            self.weight = "normal"
        elif tag == "small":
            self.size += 2
        elif tag == "big":
            self.size -= 4
        elif tag == "p":
            self.flush()
            self.cursor_y += VSTEP
        elif self.title and tag == "h1":
            self.flush()
            self.title = False
            self.size -= 2
            self.weight = "normal"
        elif tag == "p":
            self.flush()
            self.cursor_y += VSTEP

    # goes over the page nodes to render them in the display_list 
    def recurse(self, tree):
        if isinstance(tree, Text):
            for word in tree.text.split():
                self.word(word)
        else:
            if tree.attributes.get("class") == "title" and tree.tag == "h1":
                self.title = True

            self.open_tag(tree.tag)
            for child in tree.children:
                self.recurse(child)
            self.close_tag(tree.tag)

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
    
    # displays the page source with tags being in bold
    # Note: attributes values with spaces class="bla bla" will have weird output as they are not supported
    def view_source(self, tree):
        if isinstance(tree, Text):
            for word in tree.text.split():
                self.word(word)
        else:
            
            self.weight = "bold"
            self.size += 4

            attributes = ''
            for key in tree.attributes:
                if key == '/': 
                    attributes += '/'
                    continue

                attributes += key + '='
                attributes += '"' + tree.attributes.get(key) + '" ' 

            self.flush()
            self.word('<' + tree.tag + ' ' + attributes + '>')
            self.flush()

            self.weight = "normal"
            self.size -= 4

            for child in tree.children:
                self.view_source(child)

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
    def __init__(self, text, parent=None):
        self.text = text
        self.children = []
        self.parent = parent

    def __repr__(self):
        return repr(self.text)

class Element:
    def __init__(self, tag, attributes, parent):
        self.tag = tag
        self.attributes = attributes
        self.children = []
        self.parent = parent

    def __repr__(self):
        return repr("<" + self.tag + ">")


SELF_CLOSING_TAGS = [
    "area", "base", "br", "col", "embed", "hr", "img",
    "input", "link", "meta", "param", "source", "track",
    "wbr"
]   
def print_tree(node, indent=0):
    print(" " * indent, node)
    for child in node.children:
        print_tree(child, indent + 2)

# constructs the document tree
class HTMLParser:
    def __init__(self, body):
        self.body = body
        self.unfinished = []

    HEAD_TAGS = [
        "base", "basefont", "bdsound", "noscript",
        "link", "meta", "title", "style", "script",
    ]

    # fix bas written html
    def implicit_tags(self, tag):
        while True:
            open_tags = [node.tag for node in self.unfinished]
            if open_tags == [] and tag != "html":
                self.add_tag("html")
            elif open_tags == ["html"] and tag not in ["head", "body", "/html"]:
                if tag in self.HEAD_TAGS:
                    self.add_tag("head")
                else:
                    self.add_tag("body")
            elif open_tags == ["html", "head"] and tag not in ["/head"] + self.HEAD_TAGS:
                self.add_tag("/head")
            else:
                break

    # creates the text node
    def add_text(self, text):
        if text.isspace(): return
        self.implicit_tags(None)
        parent = self.unfinished[-1]
        node = Text(text, parent)
        parent.children.append(node)

    # creates the tag node
    def add_tag(self, tag):
        tag, attributes = self.get_attributes(tag)

        if tag.startswith("!"): return # throughs out comments and DOCTYPE
        self.implicit_tags(tag)
        if tag.startswith("/"):
            if len(self.unfinished) == 1: return
            node = self.unfinished.pop()
            parent = self.unfinished[-1]
            parent.children.append(node)
        elif tag in SELF_CLOSING_TAGS:
            parent = self.unfinished[-1]
            node = Element(tag, attributes, parent)
            parent.children.append(node)
        else:
            parent = self.unfinished[-1] if self.unfinished else None
            
            node = Element(tag, attributes, parent)
            self.unfinished.append(node)

    def get_attributes(self, text):
        parts = text.split()
        tag = parts[0].casefold()
        attributes = {}
        for attrpair in parts[1:]:
            if "=" in attrpair:
                key, value = attrpair.split("=", 1)

                # remove quotes
                if len(value) > 2 and value[0] in ["'", '"']:
                    value = value[1:-1]

                attributes[key.casefold()] = value
            else:
                attributes[attrpair.casefold()] = ""

        return tag, attributes

    # distributes the body between Text and Tag objects
    def parse(self):
        text = ""
        in_tag = False
        for c in self.body:
            if c == "<":
                in_tag = True
                if text: self.add_text(text)
                text = ""
            elif c == ">":
                in_tag = False
                self.add_tag(text)
                text = ""
            else: 
                text += c
                text = text.replace("&gt;", ">")
                text = text.replace("&lt;", "<")
                text = text.replace("&shy;", '\u00AD')
        
        if not in_tag and text:
            self.add_text(text)

        return self.finish()

    # finishes the unclosed tags and returns the father node
    def finish(self):
        if not self.unfinished:
            self.implicit_tags(None)
        while len(self.unfinished) > 1:
            node = self.unfinished.pop()
            parent = self.unfinished[-1]
            parent.children.append(node)
        return self.unfinished.pop()

# initializes the real browser and handles its functions
SCROLL_STEP = 100
class Browser:
    def __init__(self):
        # creates a windows and attaches it to a canvas
        self.window = tkinter.Tk()
        self.window.title("0xgouda")
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
        self.view_source = False
        if url.scheme == "about" and url.path == "blank":
            body = "Please Enter a Correct URl"
        try:    
            if url.scheme == "file":
                body = url.open_file()
            elif url.scheme in ["http", "https", "view-source"]:
                body = url.request()
            elif url.scheme == "data": 
                body = url.data

            self.view_source = url.view_source
        except:
            body = "Please Enter a Correct URL"
        
        # Gets the html document tree
        self.nodes = HTMLParser(body).parse()
        
        # returns the Layout specifications
        self.display_list = Layout(self.nodes, self.view_source).display_list

        # calculate the document total height
        self.total_height = self.display_list[-1][1] + VSTEP
        
        # displays the the text
        self.draw()

    # resizes the screen
    def resize(self, e):
        global WIDTH, HEIGHT 
        scroll_percent = self.scroll / self.total_height
        WIDTH, HEIGHT = e.width, e.height
        self.display_list = Layout(self.nodes, self.view_source).display_list

        # updates the scroll position 
        self.total_height = self.display_list[-1][1] + VSTEP
        self.scroll = min(scroll_percent * self.total_height, max(0, self.total_height - HEIGHT))

        self.draw()

    # methods to call when arrow keys or mouse wheel are triggered

    def on_mouse_wheel(self, e):
        if e.delta > 0:
            if self.scroll > 0:
                self.scroll = max(self.scroll - SCROLL_STEP, 0) 
                self.draw()
        elif e.delta < 0:
            if self.scroll + HEIGHT < self.display_list[-1][1]:
                self.scroll += SCROLL_STEP
                self.draw()

    def on_mouse_scroll(self, e):
        if e.num == 4:
            if self.scroll > 0:
                self.scroll = max(self.scroll - SCROLL_STEP, 0)  
                self.draw()
        elif e.num == 5:
            if self.scroll + HEIGHT < self.display_list[-1][1]:
                self.scroll += SCROLL_STEP
                self.draw()

    def scrollup(self, e):
        if self.scroll > 0:
            self.scroll = max(self.scroll - SCROLL_STEP, 0) 
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

            if self.total_height > HEIGHT:
                scrollbar_height = HEIGHT * (HEIGHT / self.total_height)
                scrollbar_y = HEIGHT * (self.scroll / self.total_height)

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
        print('-h or --help: show help menu\nusage:  python3 source.py http[s]://example.org\n\tpython3 source.py file://path/to/your/file\n\tpython3 source.py data:text/html,"gouda 3mk"\n\tpython3 source.py view-source:http[s]://example.org')
        exit()
    try:
        url = sys.argv[1]
    except:
        print('-h or --help: show help menu\nusage:  python3 source.py http[s]://example.org\n\tpython3 source.py file://path/to/your/file\n\tpython3 source.py data:text/html,"gouda 3mk"\n\tpython3 source.py view-source:http[s]://example.org')
        exit()

    Browser().load(URL(url))
    tkinter.mainloop()