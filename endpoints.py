#!/usr/bin/env python3
# Author: Sean Pesce

"""
API endpoints (i.e., path handlers) should be defined in this file. For learning purposes, example
handlers are defined below.
"""

import json
import time

import web_util


# Server banner delivered in the "Server: " HTTP response header (set None to disable completely)
web_util.Default.banner = 'Python Web Server by Sean Pesce'


# Define the default set of headers provided with all requests (can be overridden within
# WebPathHandler implementations)
web_util.Default.set_headers({
    'X-Example-Default-Header': 'SeanP',
    'Connection': 'close',
})


class ExampleEndpoint01(web_util.WebPathHandler):
    """
    Basic responder that handles GET requests to the path "/example01" and returns "Hello world!"
    in the response body.
    """
    METHODS = ['GET']
    PATHS = ['/example01']

    def _handle(self):
        # Set the "Content-Type" response header
        self.response.headers['Content-Type'] = 'text/plain'

        # Set the response body data (string or bytes)
        self.response.body = b'Hello world!'
        return



class ExampleEndpoint02(web_util.WebPathHandler):
    """
    Basic responder that handles PUT and POST requests to two paths ("/example2", "/example02") and
    echoes the request body in the response body.
    """
    METHODS = ['POST', 'PUT']
    PATHS = ['/example2', '/example02']

    def _handle(self):
        # Set the "Content-Type" response header
        self.response.headers['Content-Type'] = 'application/octet-stream'

        # Echo the request body data
        self.response.body = self.req_handler.req_payload
        return



class ExampleEndpoint03(web_util.WebPathHandler):
    """
    This responder demonstrates how to retrieve various information about the HTTP request and
    client/server states.
    """
    METHODS = ['GET']
    PATHS = ['/example03']

    def _handle(self):
        # Set the "Content-Type" response header
        self.response.headers['Content-Type'] = 'application/json'

        # Set the response status code (202 == ACCEPTED)
        self.response.status_code = 202

        response_data = dict()

        # Get whether server is using SSL/TLS/HTTPS
        response_data['tls'] = self.req_handler.server.using_tls

        # Get client IP address
        response_data['client_ip_addr'] = self.req_handler.client_ip

        # Get client TCP port
        response_data['client_port'] = self.req_handler.client_port

        # Get HTTP request method
        response_data['http_method'] = self.req_handler.command

        # Get request HTTP version
        response_data['http_ver'] = self.req_handler.request_version

        # Get HTTP request URL path
        response_data['path'] = self.req_handler.path

        # Get a header value from the HTTP request (case-insensitive)
        response_data['custom_header'] = self.req_handler.get_request_header('X-SeanP', '')
        
        # Get a URL query parameter value from the HTTP request
        response_data['custom_query_param'] = self.req_handler.get_url_query_param('SeanP', '', case_sensitive=True)[0]

        self.response.body = json.dumps(response_data, ensure_ascii=True)
        return



class ExampleEndpoint04(web_util.WebPathHandler):
    """
    This handler demonstrates how to use a local file as a template for the response body.
    """
    METHODS = ['GET']
    PATHS = ['/example04']
    TEMPLATE = 'assets/SeanP.png'

    def _handle(self):
        # Set the "Content-Type" response header
        self.response.headers['Content-Type'] = 'image/png'

        # Set the response body data
        self.response.body = self.template
        return



class ExampleEndpoint05(web_util.WebPathHandler):
    """
    This handler demonstrates how to use a local file as a template for the response body, with
    automatic file-parsing for specific file types (determined using file extension).

    Currently, template auto-parsing is supported for the following file types:
        *.bz2  -> Returns bytes (decompressed)
        *.gz   -> Returns bytes (decompressed)
        *.ini  -> Returns configparser.ConfigParser
        *.json -> Returns dict
        *.lzma -> Returns bytes (decompressed)
        *.xml  -> Returns xml.etree.ElementTree.Element
        *.xz   -> Returns bytes (decompressed)
        *.yaml -> Returns dict
        *.yml  -> Returns dict
    """
    METHODS = ['GET']
    PATHS = ['/example05']
    TEMPLATE = 'assets/template.json'
    PARSE_TEMPLATE = True
    TEMPLATE_ENCODING = 'utf8'

    def _handle(self):
        # Set the "Content-Type" response header
        self.response.headers['Content-Type'] = 'application/json'

        # Add a field to the pre-parsed template data
        self.template['timestamp'] = int(time.time() * 1000)

        # Set the response body data
        self.response.body = json.dumps(self.template, ensure_ascii=True)
        return



class ExampleEndpoint06(web_util.WebPathHandler):
    """
    Basic responder that handles GET requests to the path "/example06" and returns "Hello world!"
    in the response body, but HEAD and OPTIONS requests are disabled.
    """
    METHODS = ['GET']
    PATHS = ['/example06']
    DISABLE_HEAD_REQUESTS = True
    DISABLE_OPTIONS_REQUESTS = True

    def _handle(self):
        # Set the "Content-Type" response header
        self.response.headers['Content-Type'] = 'text/plain'

        # Set the response body data (string or bytes)
        self.response.body = b'Hello world!'
        return

