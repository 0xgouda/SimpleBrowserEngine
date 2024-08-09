import socket
import ssl

class URL:
    def __init__(self, url):
        # ensures that https or http is in use
        self.scheme, url = url.split("://", 1)
        assert self.scheme in ["http", "https"]

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
    
    # sends the request and receives the response
    def request(self):
        # create a socket and establish the connection
        s = socket.socket(
            family = socket.AF_INET,
            type = socket.SOCK_STREAM,
            proto = socket.IPPROTO_TCP
        )
        s.connect((self.host, self.port))
        
        # create the ssl context
        if self.scheme == "https":
            ctx = ssl.create_default_context()
            s = ctx.wrap_socket(s, server_hostname=self.host)

        # sends the request
        request = "GET {} HTTP/1.1\r\n".format(self.path)
        request += "Host: {}\r\n".format(self.host)
        request += "Connection: close\r\n"
        request += "User-Agent: the browser of gouda\r\n"
        request += "\r\n"
        s.send(request.encode("utf8"))

        # receiving the response
        response = s.makefile("r", encoding="utf8", newline="\r\n")

        # assigning reponse to variables
        statusline = response.readline()
        version, status, explanation = statusline.split(" ", 2)

        response_headers = {}
        while True:
            line = response.readline()
            if line == "\r\n": break
            header, value = line.split(":", 1)
            response_headers[header.casefold()] = value.strip()

        # ensures that no encoding is used
        assert "transfer-encoding" not in response_headers
        assert "content-encoding" not in response_headers

        # returning the body
        content = response.read()
        s.close()
        return content

def show(body):
    # printing page text
    in_tag = False
    for c in body:
        if c == "<":
            in_tag = True
        elif c == ">":
            in_tag = False
        elif not in_tag:
            print(c, end="")
    
def load(url):
    body = url.request()
    show(body)

if __name__ == "__main__":
    import sys
    load(URL(sys.argv[1]))