# initializes the real browser and handles its functions

import tkinter
from layout import Layout
import parser
import config

SCROLL_STEP = 100
class Browser:
    def __init__(self):
        # creates a windows and attaches it to a canvas
        self.window = tkinter.Tk()
        self.window.title("0xgouda")
        self.canvas = tkinter.Canvas(
            self.window,
            width = config.WIDTH,
            height = config.HEIGHT
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
        self.nodes = parser.HTMLParser(body).parse()
        
        # returns the Layout specifications
        self.display_list = Layout(self.nodes, self.view_source).display_list

        # calculate the document total height
        self.total_height = self.display_list[-1][1] + config.VSTEP
        
        # displays the the text
        self.draw()

    # resizes the screen
    def resize(self, e):
        scroll_percent = self.scroll / self.total_height
        config.WIDTH, config.HEIGHT = e.width, e.height
        self.display_list = Layout(self.nodes, self.view_source).display_list

        # updates the scroll position 
        self.total_height = self.display_list[-1][1] + config.VSTEP
        self.scroll = min(scroll_percent * self.total_height, max(0, self.total_height - config.HEIGHT))

        self.draw()

    # methods to call when arrow keys or mouse wheel are triggered

    def on_mouse_wheel(self, e):
        if e.delta > 0:
            if self.scroll > 0:
                self.scroll = max(self.scroll - SCROLL_STEP, 0) 
                self.draw()
        elif e.delta < 0:
            if self.scroll + config.HEIGHT < self.display_list[-1][1]:
                self.scroll += SCROLL_STEP
                self.draw()

    def on_mouse_scroll(self, e):
        if e.num == 4:
            if self.scroll > 0:
                self.scroll = max(self.scroll - SCROLL_STEP, 0)  
                self.draw()
        elif e.num == 5:
            if self.scroll + config.HEIGHT < self.display_list[-1][1]:
                self.scroll += SCROLL_STEP
                self.draw()

    def scrollup(self, e):
        if self.scroll > 0:
            self.scroll = max(self.scroll - SCROLL_STEP, 0) 
            self.draw()

    def scrolldown(self, e):
        if self.scroll + config.HEIGHT < self.display_list[-1][1]:
            self.scroll += SCROLL_STEP
            self.draw()


    def draw(self):
        self.canvas.delete("all")
        try:
            for x, y, word, font in self.display_list:
                # excludes the chars under and above the viewport
                if (y > self.scroll + config.HEIGHT or y + config.VSTEP < self.scroll): continue
            
                self.canvas.create_text(x, y - self.scroll, text=word, font=font, anchor="nw")

            if self.total_height > config.HEIGHT:
                scrollbar_height = config.HEIGHT * (config.HEIGHT / self.total_height)
                scrollbar_y = config.HEIGHT * (self.scroll / self.total_height)

                self.canvas.create_rectangle(
                    config.WIDTH - 10,
                    scrollbar_y,
                    config.WIDTH,
                    scrollbar_y + scrollbar_height,
                    fill="#C0C0C0"
                )
        except:
            pass