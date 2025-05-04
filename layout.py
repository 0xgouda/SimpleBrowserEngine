# processes all the page the body view and saves it to a list

import tkinter.font
from nodes import Text
import config

# caching the fonts to speed up text processing
FONTS = {}
def get_font(size, weight, style):
    key = (size, weight, style)
    if key not in FONTS:
        font = tkinter.font.Font(size=size, weight=weight, slant=style)
        tkinter.Label(font=font)
        FONTS[key] = font
    
    return FONTS[key]

TAG_ACTIONS = {
    "i": {"style": "italic"},
    "b": {"weight": "bold"},
    "small": {"size": -2},
    "big": {"size": 4},
    "br": {"flush": True},
    "h1": {"flush": True, "size": 4, "weight": "bold"}
}

class Layout:
    def __init__(self, dom_root, view_source_enabled):
        self.display_list = []
        self.cursor_x = config.HSTEP
        self.cursor_y = config.VSTEP
        self.weight = "normal"
        self.style = "roman"
        self.size = 12
        self.line = []
        self.view_source_enabled = view_source_enabled

        self.render_node(dom_root)
        self.flush_line_buffer()
    
    def apply_tag_actions(self, tag):
        if tag not in TAG_ACTIONS: return 
        
        old_values = {}
        for key, value in TAG_ACTIONS[tag].items():
            if key == "flush":
                self.flush_line_buffer()
                continue

            if isinstance(value, int):
                value += self.key

            old_values[key] = self.key
            setattr(self, key, value)

        yield

        for key in TAG_ACTIONS[tag]:
            setattr(self, key, old_values[key])
         
    def render_node(self, node):
        if isinstance(node, Text):
            for word in node.text.split():
                self.word(word)
            return

        if not self.view_source_enabled:
            self.apply_tag_actions(node.tag)
            for child in node.children:
                self.render_node(child)
            self.apply_tag_actions(node.tag)
            return

        attributes = ''
        for key, value in node.attributes.items():
            attributes += f'{key}="{value}"'

        self.flush_line_buffer()
        self.word(f"<{node.tag} {attributes}>")
        self.flush_line_buffer()

        for child in node.children:
            self.render_node(child)
        
        if node.tag not in config.SELF_CLOSING_TAGS:
            self.flush_line_buffer()
            self.word('</' + node.tag + '>')
            self.flush_line_buffer()

    def flush_line_buffer(self):
        if not self.line: return

        metrics = [font.metrics() for x, word, font in self.line]
        max_ascent = max([metric["ascent"] for metric in metrics])
        top_baseline = self.cursor_y + 1.25 * max_ascent

        for x, word, font in self.line:
            y = top_baseline - font.metrics("ascent")
            self.display_list.append((x, y, word, font))

        max_descent = max([metric["descent"] for metric in metrics])
        self.cursor_y = top_baseline + 1.25 * max_descent
        self.cursor_x = config.HSTEP
        self.line = []
    
    # determines the font and x-cords of the word
    def word(self, word):
        font = get_font(self.size, self.weight, self.style)
        w = font.measure(word)

        if self.cursor_x + w > config.WIDTH - config.HSTEP:
            self.flush_line_buffer()
        else:
            self.line.append((self.cursor_x, word, font))
            self.cursor_x += w + font.measure(" ")