# Parses the HTML and Creates the DOM

from nodes import Text, Element

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