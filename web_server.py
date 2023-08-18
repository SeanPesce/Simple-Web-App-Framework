#!/usr/bin/env python3
# Author: Sean Pesce

# References:
#   https://docs.python.org/3/library/ssl.html
#   https://docs.python.org/3/library/http.server.html
#   https://stackoverflow.com/questions/19705785/python-3-simple-https-server

# Shell command to create a self-signed TLS certificate and private key:
#    openssl req -new -newkey rsa:4096 -x509 -sha256 -days 365 -nodes -out cert.crt -keyout private.key

import gzip
import http.server, http.client
import socket
import ssl
import sys

from urllib.parse import urlparse, parse_qs

import web_util
from endpoints import *



class WebAppHttpHandler(http.server.BaseHTTPRequestHandler, web_util.WebPathMap):
    protocol_version = 'HTTP/1.1'

    def version_string(self):
        # Override 'Server: BaseHTTP...' header in base implementation
        return web_util.Default.banner
    
    def send_header(self, keyword, value):
        if keyword.lower() == 'server' and self.version_string() is None:
            return None
        return super().send_header(keyword, value)

    def _init_response(self):
        self.pending_resp = None
        parsed_path = urlparse(self.path)
        self.query = parse_qs(parsed_path.query)
        # # De-list-ify single-value URL query parameters
        # for key in self.query:
        #     if len(self.query[key]) == 1:
        #         self.query[key] = self.query[key][0]
        has_content_len_hdr = False
        for hdr in self.headers:  # Request headers
            hdr_lower = hdr.lower()
            if hdr_lower == 'content-length':
                try:
                    int(self.headers[hdr])
                    has_content_len_hdr = True
                except ValueError:
                    pass
        self.primary_path = parsed_path.path
        self.req_payload = b''
        if self.command in ('POST', 'PUT') or has_content_len_hdr:
            content_len = 0
            compression = None
            chunked = False
            for hdr in self.headers:  # Request headers
                hdr_lower = hdr.lower()
                if hdr_lower == 'content-length':
                    try:
                        content_len = int(self.headers[hdr])
                    except ValueError:
                        pass
                elif hdr_lower == 'content-encoding':
                    for cs in web_util.COMPRESSION_SCHEMES:
                        if cs in self.headers[hdr]:
                            compression = self.headers[hdr]
                            break
                elif hdr_lower == 'transfer-encoding':
                    if 'chunked' in self.headers[hdr]:
                        chunked = True
                    else:
                        pass  # @TODO: Support other/multiple transfer encodings?
            if content_len > 0:
                recv_data = self.rfile.read(content_len)
                while recv_data is not None and recv_data != b'':
                    self.req_payload += recv_data
                    content_len -= len(recv_data)
                    recv_data = self.rfile.read(content_len)

            elif chunked:
                while True:
                    chunk_sz = self.rfile.readline().strip()
                    chunk_sz = int(chunk_sz, 16)
                    self.req_payload += self.rfile.read(chunk_sz)
                    self.rfile.read(2)  # Skip past chunk tail ('\r\n'); note that this stream is not seekable
                    if chunk_sz == 0:
                        break

            if compression is not None:
                # @TODO: Support other/multiple content encodings
                if 'gzip' in compression:
                    self.req_payload = gzip.decompress(self.req_payload)
        return


    def _send_pending_response(self):
        self.send_response(self.pending_resp.status_code)
        #self.pending_resp.headers['Date'] = web_util.date_for_header()
        if len(self.pending_resp.body) > 0:
            self.pending_resp.headers['Content-Length'] = str(len(self.pending_resp.body))

        for hdr in self.headers:  # Request headers
            print(f'    {hdr}: {self.headers[hdr]}')
        print()
        if len(self.req_payload) > 0:
            print(f'    {self.req_payload}\n')

        print(f'{self.protocol_version} {self.pending_resp.status_code} {http.client.responses[self.pending_resp.status_code]}')
        for hdr in self.pending_resp.headers:  # Response headers
            print(f'    {hdr}: {self.pending_resp.headers[hdr]}')
            self.send_header(hdr, self.pending_resp.headers[hdr])
        if len(self.pending_resp.body) > 0:
            print(f'\n    {self.pending_resp.body[:1000]}\n\n')
        else:
            print('\n')

        self.end_headers()
        # If HEAD request, don't send the response body data
        if self.command not in ('HEAD', 'OPTIONS') and len(self.pending_resp.body) > 0:
            self.wfile.write(self.pending_resp.body)# + b'\r\n\r\n')
        return


    def _build_and_send_response(self):
        self._init_response()

        for m in self.__class__.PATHS:
            if (m == self.command or self.command in ('HEAD', 'OPTIONS')) and self.primary_path in self.__class__.PATHS[m]:
                path_handler = self.__class__.PATHS[m][self.primary_path]
                if (self.command == 'HEAD' and path_handler.DISABLE_HEAD_REQUESTS) or (self.command == 'OPTIONS' and path_handler.DISABLE_OPTIONS_REQUESTS):
                    self.pending_resp = web_util.RESP_BAD_METHOD()
                    break
                elif self.command == 'OPTIONS':
                    self.pending_resp = web_util.RESP_NO_CONTENT()
                    self.pending_resp.headers['Allow'] = ''
                    for method in self.__class__.PATHS:
                        if self.primary_path in self.__class__.PATHS[method]:
                            self.pending_resp.headers['Allow'] += f'{method}, '
                    self.pending_resp.headers['Allow'] = self.pending_resp.headers['Allow'][:-2]
                    break
                elif path_handler is None:
                    self.pending_resp = web_util.RESP_OK()
                    break

                self.pending_resp = path_handler(self, web_util.RESP_OK()).handle()
                assert self.pending_resp is not None, 'Path handler returned None response'
                break

            elif self.primary_path in self.__class__.PATHS[m]:
                self.pending_resp = web_util.RESP_BAD_METHOD()

        if self.pending_resp is None:
            self.pending_resp = web_util.RESP_NOT_FOUND()

        self._send_pending_response()


    def do_GET(self):
        self._build_and_send_response()


    def do_HEAD(self):
        self._build_and_send_response()


    def do_OPTIONS(self):
        self._build_and_send_response()


    def do_POST(self):
        self._build_and_send_response()


    def do_PUT(self):
        self._build_and_send_response()


    @property
    def client_ip(self):
        return self.client_address[0]


    @property
    def client_port(self):
        return self.client_address[1]


    def get_request_header(self, key, default_val):
        """
        Case-insensitive
        """
        if key in self.headers:
            return self.headers[key]
        return default_val


    def get_url_query_param(self, key, default_val, case_sensitive=True):
        if case_sensitive and key in self.query:
            return self.query[key]
        elif not case_sensitive:
            key = key.lower()
            for k in self.query.keys():
                if k.lower() == key:
                    return self.query[k]
        return [ default_val, ]



def serve(host, port, cert_fpath, privkey_fpath):
    """
    Begin listening on the specified interface (host) and port. If file paths are provided for a
    certificate and private key, the server will automatically use TLS (HTTPS). If not, the server
    will automatically serve plaintext HTTP.
    """
    server_address = (host, port)
    httpd = http.server.ThreadingHTTPServer(server_address, WebAppHttpHandler)
    httpd.using_tls = False
    if cert_fpath and privkey_fpath:
        httpd.using_tls = True
        context = ssl.SSLContext(ssl.PROTOCOL_TLS)
        context.load_cert_chain(certfile=cert_fpath, keyfile=privkey_fpath, password='')
        httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
    print(f'Listening for HTTP{"S" if httpd.using_tls else ""} connections on {host}:{port}\n')
    httpd.serve_forever()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(f'Usage:\n  {sys.argv[0]} <port> [PEM certificate file] [private key file]')
        sys.exit()
    
    INTERFACE = '0.0.0.0'
    PORT = int(sys.argv[1])
    CERT_FPATH = None
    PRIVKEY_FPATH = None
    if len(sys.argv) > 3:
        CERT_FPATH = sys.argv[2]
        PRIVKEY_FPATH = sys.argv[3]
    INTERFACE = socket.gethostbyname(INTERFACE)
    
    serve(INTERFACE, PORT, CERT_FPATH, PRIVKEY_FPATH)
