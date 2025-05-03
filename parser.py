# Parses the HTML and Creates the DOM

from nodes import Text, Element
from config import SELF_CLOSING_TAGS

def print_tree(node, indent=0):
    print(" " * indent, node)
    for child in node.children:
        print_tree(child, indent + 2)

class HTMLParser:
    def __init__(self, body):
        self.body = body
        self.unfinished = []

    HEAD_TAGS = [
        "base", "basefont", "bdsound", "noscript",
        "link", "meta", "title", "style", "script",
    ]

    # fix bad written html
    def implicit_tags(self, tag):
        while True:
            open_tags = [node.tag for node in self.unfinished]
            if open_tags == [] and tag != "html":
                self.add_tag("html")
            elif open_tags[-1] == "html" and tag not in ["head", "body", "/html"]:
                if tag in self.HEAD_TAGS:
                    self.add_tag("head")
                else:
                    self.add_tag("body")
            elif open_tags[-1] == "head" and tag not in self.HEAD_TAGS:
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
        unfinished_len = len(self.unfinished)

        def finish_tag():
            node = self.unfinished.pop()
            parent = self.unfinished[-1]
            parent.children.append(node)

        if tag.startswith("!"): return # throughs out comments and DOCTYPE
        self.implicit_tags(tag)
        if tag.startswith("/"):
            if unfinished_len <= 1: return
            finish_tag()
        elif tag in SELF_CLOSING_TAGS:
            parent = self.unfinished[-1]
            node = Element(tag, attributes, parent)
            parent.children.append(node)
        else:
            if tag == "p" and unfinished_len and tag == self.unfinished[-1].tag:
                return
            
            parent = self.unfinished[-1] if unfinished_len else None
            
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
    
    def is_comment(self, text):
        return not len(text) < 3 and text[:3] == "!--"

    # distributes the body between Text and Tag objects
    def parse(self):
        text = ""
        in_tag = False
        is_comment = False
        is_script = False

        for c in self.body:

            if len(text) >= 7 and text[-8:] + c == "</script>": 
                is_script = False
                self.add_text(text[:-8])
                text = "/script"
                
            is_comment = self.is_comment(text)

            if c == "<" and not is_script and not is_comment:
                in_tag = True
                if text: self.add_text(text)
                text = ""

            elif c == ">" and not is_script and not is_comment:
                in_tag = False
                text = text.replace("&gt;", ">").replace("&lt;", "<")
                self.add_tag(text)
                text = ""

                try:
                    if self.unfinished[-1].tag == "script": is_script = True
                except: pass

            elif text[-2:] + c == "-->" and is_comment:
                is_comment = False
                text = ""
            else: 
                text += c
        
        if not in_tag and text:
            self.add_text(text)

        return self.finish()

    # finishes the unclosed tags and returns the father node
    def finish(self):
        while len(self.unfinished) > 1:
            node = self.unfinished.pop()
            parent = self.unfinished[-1]
            parent.children.append(node)
        return self.unfinished.pop()