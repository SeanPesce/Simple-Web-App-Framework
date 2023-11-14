#!/usr/bin/env python3
# Author: Sean Pesce

import abc
import bz2
import configparser
import dataclasses
import datetime
import gzip
import json
import lzma
import os
import urllib3
import yaml

from xml.etree import ElementTree


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


COMPRESSION_SCHEMES = ['gzip', 'x-gzip', 'compress', 'deflate', 'br']


def random_uuid():
    return f'{os.urandom(4).hex()}-{os.urandom(2).hex()}-{os.urandom(2).hex()}-{os.urandom(2).hex()}-{os.urandom(6).hex()}'


def date_for_header():
    return datetime.datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')


class Default:
    _headers = {}
    banner = 'SeanP'

    @classmethod
    def headers(cls):
        return dict(cls._headers)
    
    @classmethod
    def set_headers(cls, headers):
        assert type(headers) == dict, f'Expected dictionary but received type(headers)={type(headers)}'
        headers = dict(headers)
        for header in headers.keys():
            assert type(header) == str, f'Expected string but received type(header)={type(header)}'
            bad_chars = ' :\r\n\t\b\0'
            for bad_char in bad_chars:
                assert bad_char not in header, f'Header key contained invalid character: \'{bad_char}\''
            header_value = headers[header]
            assert type(header_value) == str, f'Expected string but received type(header_value)={type(header_value)}'
            headers[header] = header_value.replace('\n', ' ').replace('\r', ' ')
        
        cls._headers = headers
        return cls.headers()


@dataclasses.dataclass
class ResponseContainer:
    status_code: int = 404
    headers: dict = dataclasses.field(default_factory=Default.headers)
    body: bytes = b''

    def copy(self):
        new_inst = ResponseContainer()
        for f in dataclasses.fields(self):
            old_attr = getattr(self, f.name)
            attr_cls = old_attr.__class__
            setattr(new_inst, f.name, attr_cls(old_attr))
        return new_inst


def RESP_OK():
    return ResponseContainer(status_code=200)

def RESP_ACCEPTED():
    return ResponseContainer(status_code=202)

def RESP_NO_CONTENT():
    return ResponseContainer(status_code=204)

def RESP_BAD_REQUEST():
    return ResponseContainer(status_code=400)

def RESP_NOT_FOUND():
    return ResponseContainer(status_code=404)

def RESP_BAD_METHOD():
    return ResponseContainer(status_code=405)


def read_file(fpath, parse=False, encoding='utf8'):
    """
    Read file and (optionally) automatically parse supported file types.

    Automatically-parsed files (based on extension):
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
    data = b''
    with open(fpath, 'rb') as f:
        read_data = f.read()
        while read_data != b'':
            data += read_data
            read_data = f.read()

    if not parse:
        return data

    file_extension = os.path.splitext(fpath)[1]
    if file_extension == '.bz2':
        data = bz2.decompress(data)
    elif file_extension == '.gz':
        data = gzip.decompress(data)
    elif file_extension == '.ini':
        data = configparser.ConfigParser()
        data.read(fpath)
    elif file_extension == '.json':
        data = json.loads(data)
    elif file_extension == '.xml':
        data = ElementTree.fromstring(data)
    elif file_extension in ('.xz', '.lzma'):
        data = lzma.decompress(data)
    elif file_extension in ('.yaml', '.yml'):
        data = yaml.safe_load(data)
    return data


class WebPathMap:
    CONNECT_PATHS = {
        '/': None
    }
    DELETE_PATHS = {
        '/': None
    }
    GET_PATHS = {
        '/': None
    }
    PATCH_PATHS = {
        '/': None
    }
    POST_PATHS = {
        '/': None
    }
    PUT_PATHS = {
        '/': None
    }
    PATHS = {
        'CONNECT': CONNECT_PATHS,
        'DELETE': DELETE_PATHS,
        'GET': GET_PATHS,
        'PATCH': PATCH_PATHS,
        'POST': POST_PATHS,
        'PUT': PUT_PATHS,
    }
    
    CONNECT_REGEX_PATHS = {}
    DELETE_REGEX_PATHS = {}
    GET_REGEX_PATHS = {}
    PATCH_REGEX_PATHS = {}
    POST_REGEX_PATHS = {}
    PUT_REGEX_PATHS = {}
    REGEX_PATHS = {
        'CONNECT': CONNECT_REGEX_PATHS,
        'DELETE': DELETE_REGEX_PATHS,
        'GET': GET_REGEX_PATHS,
        'PATCH': PATCH_REGEX_PATHS,
        'POST': POST_REGEX_PATHS,
        'PUT': PUT_REGEX_PATHS,
    }


class WebPathHandler(abc.ABC):
    def __init__(self, req_handler, response_init=None):
        self.req_handler = req_handler
        assert self.req_handler is not None, f'{self.__class__.__name__} : req_handler={req_handler}'
        self.response = response_init.copy()
        if self.response is None:
            self.response = RESP_OK()
        return


    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if not hasattr(cls, 'PATHS'):
            cls.PATHS = list()
        if not hasattr(cls, 'REGEX_PATHS'):
            cls.REGEX_PATHS = list()
        
        if len(cls.METHODS) == 0:
            raise KeyError('At least one method must be defined')
        if len(cls.PATHS) + len(cls.REGEX_PATHS) == 0:
            raise KeyError('At least one path must be defined')

        if not hasattr(cls, 'DISABLE_HEAD_REQUESTS'):
            cls.DISABLE_HEAD_REQUESTS = False

        if not hasattr(cls, 'DISABLE_OPTIONS_REQUESTS'):
            cls.DISABLE_OPTIONS_REQUESTS = False

        if not hasattr(cls, 'RESPONSE_ENCODING'):
            cls.RESPONSE_ENCODING = 'utf8'

        if not hasattr(cls, 'TEMPLATE'):
            cls.TEMPLATE = None

        if not hasattr(cls, 'PARSE_TEMPLATE'):
            cls.PARSE_TEMPLATE = False

        if not hasattr(cls, 'TEMPLATE_ENCODING'):
            cls.TEMPLATE_ENCODING = cls.RESPONSE_ENCODING
        
        assert type(cls.DISABLE_HEAD_REQUESTS) == bool, f'Expected boolean value but encountered {type(cls.DISABLE_HEAD_REQUESTS)}'
        assert type(cls.DISABLE_OPTIONS_REQUESTS) == bool, f'Expected boolean value but encountered {type(cls.DISABLE_OPTIONS_REQUESTS)}'
        assert type(cls.RESPONSE_ENCODING) == str, f'Expected string value but encountered {type(cls.RESPONSE_ENCODING)}'
        assert type(cls.PARSE_TEMPLATE) == bool, f'Expected boolean value but encountered {type(cls.PARSE_TEMPLATE)}'
        assert type(cls.TEMPLATE_ENCODING) == str, f'Expected string value but encountered {type(cls.TEMPLATE_ENCODING)}'

        for method in cls.METHODS:
            if method not in WebPathMap.PATHS:
                raise KeyError(f'Unsupported HTTP method: {cls.METHOD}')

            for path in cls.PATHS:
                if path in WebPathMap.PATHS[method]:
                    print(f'[Warning] Overwriting {method} {path}')
                WebPathMap.PATHS[method][path] = cls

            for path in cls.REGEX_PATHS:
                if path in WebPathMap.REGEX_PATHS[method]:
                    print(f'[Warning] Overwriting {method} {path} (RegEx)')
                WebPathMap.REGEX_PATHS[method][path] = cls
        return


    @abc.abstractmethod
    def _handle(self):
        """
        Handle the incoming request and build a populated ResponseContainer in self.response
        """
        pass


    def handle(self):
        self.template = None
        if self.TEMPLATE is not None:
            self.template = read_file(self.TEMPLATE, parse=self.PARSE_TEMPLATE, encoding=self.TEMPLATE_ENCODING)

        self._handle()
        if type(self.response.body) == str:
            self.response.body = self.response.body.encode(self.RESPONSE_ENCODING)
        return self.response
