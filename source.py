import socket
import ssl

class URL:
    def __init__(self, url, redirect_count):
        # checks if view-source scheme is in use
        self.scheme, url = url.split(":", 1)
        assert self.scheme in ["http", "https", "file", "data", "view-source"]
        self.view_source = False
        if self.scheme == "view-source":
            self.view_source = True

        # save the number of redirects
        self.redirect_count = redirect_count

        # no socket connections exist
        self.s = None
        self.connection = None

        # check if data scheme is in use
        if self.scheme == "data":
            self.mediatype, self.data = url.split(",", 1)
            return

        # ensures that https or http or data or file is in use
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
        
        # create the ssl contexsocket 
        if self.scheme == "https":
            ctx = ssl.create_default_context()
            s = ctx.wrap_socket(s, server_hostname=self.host)
        
        return s

    # sends the request and receives the response
    def request(self):
        
        if self.s is None or self.connection != self.host:
            self.s = self.create_socket()

        # sends the request
        request = "GET {} HTTP/1.1\r\n".format(self.path)
        request += "Host: {}\r\n".format(self.host)
        request += "User-Agent: the browser of gouda\r\n"
        request += "\r\n"
        self.s.send(request.encode("utf8"))

        # receiving the response
        response = self.s.makefile("r", encoding="utf8", newline="\r\n")

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

        # handle redirects
        status = int(status)
        if status >= 300 and status < 400:
            if self.redirect_count > 5:
                return "Error due to too much redirects"

            self.redirect_count += 1

            location = response_headers["location"]
            if location[0] == "/":
                self.path = location
            else:
                self.__init__(location, self.redirect_count)
            return self.request()
        else:
            # returning the body
            content = response.read(int(response_headers.get("content-length", 0)))
            self.close()
            return content

    # closes the socket connection
    def close(self):
        if self.s:
            self.s.close()
            self.s = None

    def open_file(self):
        file = open(self.host, 'r')
        return file.read()


def show(body):
    # printing page text
    in_tag = False
    result = ""
    for c in body:
        if c == "<":
            in_tag = True
        elif c == ">":
            in_tag = False
        elif not in_tag:   
            result += c

    print(result.replace("&lt;", "<").replace("&gt;", ">"))
    
def load(url):
    if url.scheme == "file":
        body = url.open_file()
    elif url.scheme in ["http", "https"]:
        body = url.request()
    elif url.scheme == "data": 
        body = url.data
    
    if url.view_source == True:
        print(body)
    else:
        show(body)

if __name__ == "__main__":
    import sys
    
    try:
        url = sys.argv[1]
    except IndexError:
        url = "file:///home/ahmed/index.html"

    load(URL(url, 0))
