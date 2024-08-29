# processes all the page text and saves it to a list

import tkinter.font
from nodes import Text
import config

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

class Layout:
    def __init__(self, tree, view_source):
        self.display_list = []
        self.cursor_x = config.HSTEP
        self.cursor_y = config.VSTEP
        self.weight = "normal"
        self.style = "roman"
        self.size = 12
        self.line = []
        self.title = False

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
            self.cursor_y += config.VSTEP
        elif self.title and tag == "h1":
            self.flush()
            self.title = False
            self.size -= 2
            self.weight = "normal"
        elif tag == "p":
            self.flush()
            self.cursor_y += config.VSTEP

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
            self.display_list.append((((x + ((config.WIDTH - measures) / 2)) if self.title else x), y, word, font))

        max_descent = max([metric["descent"] for metric in metrics])
        self.cursor_y = baseline + 1.25 * max_descent
        self.cursor_x = config.HSTEP
        self.line = []
    
    # displays the page source with tags being in bold
    # Note: attributes values with spaces class="bla bla" will have weird output as they are not supported
    def view_source(self, tree):
        if isinstance(tree, Text):
            self.weight = "bold"
            for word in tree.text.split():
                self.word(word)
            self.weight = "normal"
        else:
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

            for child in tree.children:
                self.view_source(child)
            
            if tree.tag not in config.SELF_CLOSING_TAGS:
                self.flush()
                self.word('</' + tree.tag + '>')
                self.flush()

    # determines the shape and coordinates of the letter
    def word(self, word):
        font = get_font(self.size, self.weight, self.style)
        w = font.measure(word)

        if self.cursor_x + w > config.WIDTH - config.HSTEP:
            self.flush()
        else:
            self.line.append((self.cursor_x, word, font))
            self.cursor_x += w + font.measure(" ")