#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import base64
import configparser
import getopt
import hashlib
import hmac
import json
import logging
import subprocess
import sys
import time
from os import path
from enum import Enum, unique
from urllib.parse import parse_qs, urlparse
from http.server import BaseHTTPRequestHandler, HTTPServer

@unique
class Provider(Enum):
    Github = 0
    Gitee = 1
    Gitlab = 2
    Custom = 3

class RequestHandler(BaseHTTPRequestHandler):

    def __parse_provider(self):
        '''parse the provider type'''
        global config
        # Github
        if 'X-GitHub-Event' in self.headers:
            return Provider.Github
        # Gitee
        elif 'X-Gitee-Event' in self.headers:
            return Provider.Gitee
        # Gitlab
        elif 'X-Gitlab-Event' in self.headers:
            return Provider.Gitlab
        # Custom
        elif 'custom' in config:
            header_name = config.get('custom', 'header_name')
            header_value = config.get('custom', 'header_value')
            if header_name in self.headers and self.headers.get(header_name).startswith(header_value):
                return Provider.Custom
        # Unkown provider
        return None

    def __parse_data(self):
        '''parse the request content'''
        content_type = self.headers.get('Content-Type').lower()
        content_len = int(self.headers.get('Content-Length', 0))
        payload = self.rfile.read(content_len)
        try:
            # json
            if content_type.startswith('application/json'):
                return payload, json.loads(payload.decode('utf-8'))
            # usl encoded
            elif content_type.startswith('application/x-www-form-urlencoded'):
                data = parse_qs(payload.decode('utf-8'), keep_blank_values = 1)
                if 'payload' in data:
                    try:
                        return payload, json.loads(data['payload'][0])
                    except:
                        pass
                return payload, data
        except:
            pass
        # other types are unsupported
        return payload, None

    def do_GET(self):
        '''does not handle the GET requests, direct response 403.'''
        self.send_error(403, 'Forbidden')

    def do_POST(self):
        '''handling the POST requests.'''
        global config
        provider = self.__parse_provider()
        payload, post_data = self.__parse_data()
        repo_name = None

        if post_data is None:
            logging.warning('Unsupported Request: {}'.format(payload))
            self.send_error(400)
            return

        if provider is Provider.Github:
            # Github
            if config.getboolean('github', 'verify'):
                # Signature calculation and verification
                request_signature = self.headers.get('X-Hub-Signature')
                if request_signature is None:
                    logging.warning('Missing Signature')
                    self.send_error(401)
                    return
                secret = bytes(config.get('github', 'secret'), encoding = 'utf-8')
                verify_signature = 'sha1=' + hmac.new(secret, payload, hashlib.sha1).hexdigest()
                if request_signature != verify_signature:
                    logging.warning('Invalid Signature')
                    self.send_error(401)
                    return
            if 'repository' in post_data and 'full_name' in post_data['repository']:
                repo_name = post_data['repository']['full_name']

        elif provider is Provider.Gitee:
            # Gitee
            if config.getboolean('gitee', 'verify'):
                # Signature calculation and verification
                request_signature = self.headers.get('X-Gitee-Token')
                if request_signature is None:
                    logging.warning('Missing Signature or Password')
                    self.send_error(401)
                    return
                query = parse_qs(urlparse(self.path).query)
                request_timestamp = int(self.headers.get('X-Gitee-Timestamp'))
                secret = config.get('gitee', 'secret')
                if 'sign' in query:
                    # for signature
                    secret_encoded = bytes(secret, encoding = 'utf-8')
                    pending_to_signature = bytes('{}\n{}'.format(request_timestamp, secret), encoding = 'utf-8')
                    verify_signature = base64.b64encode(hmac.new(secret_encoded, pending_to_signature, digestmod=hashlib.sha256).digest()).decode('utf-8')
                    if request_signature != verify_signature:
                        logging.warning('Invalid Signature')
                        self.send_error(401)
                        return
                elif request_signature != secret:
                    # for password
                    logging.warning('Invalid Password')
                    self.send_error(401)
                    return
            # Get repository name
            if 'repository' in post_data and 'full_name' in post_data['repository']:
                repo_name = post_data['repository']['full_name']

        elif provider is Provider.Gitlab:
            # Gitlab
            if config.getboolean('gitlab', 'verify'):
                request_token = self.headers.get('X-Gitlab-Token')
                secret = config.get('gitee', 'secret')
                if request_token != secret:
                    logging.warning('Invalid Token')
                    self.send_error(401)
                    return
            # Get repository name
            if 'project' in post_data and 'path_with_namespace' in post_data['project']:
                repo_name = post_data['project']['path_with_namespace']

        elif provider is Provider.Custom:
            # Custom
            header_token = config.get('custom', 'header_token', fallback = 'X-Custom-Token')
            if config.getboolean('custom', 'verify') and header_token in self.headers:
                request_token = self.headers.get(header_token)
                secret = config.get('custom', 'secret')
                if request_token != secret:
                    logging.warning('Invalid Token')
                    self.send_error(401)
                    return
            # Get repository name
            path = config.get('custom', 'name_path').split('.')
            value = post_data
            for step in path:
                if step in value:
                    value = value[step]
            if isinstance(value, str):
                repo_name = value
        else:
            logging.warning('Unknow provider')
            self.send_error(412)
            return

        if repo_name is not None:
            if repo_name in config:
                cwd = config.get(repo_name, 'cwd')
                cmd = config.get(repo_name, 'cmd')
                logging.info('[{}] Execute: {}'.format(repo_name, cmd))
                process = subprocess.Popen(cmd, cwd = cwd, shell = True, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
                for line in process.stdout:
                    logging.info('[{}] Output: {}'.format(repo_name, line.rstrip()))
            else:
                logging.warning('No repository setting: "{}".'.format(repo_name))
            # successful
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'OK')
        else:
            logging.warning('Missing repository information.')
            self.send_error(404)

def help_infos():
    '''Print help infos'''
    print('usage: webhooks.py -c <configuration_file>')
    sys.exit(0)

def main(argv):
    global config
    # default configuration file
    conf_file = '/usr/local/etc/webhooks.ini'
    # handle arguments
    try:
        opts, _ = getopt.getopt(argv, 'hc:', ['config='])
    except getopt.GetoptError:
        help_infos()

    for opt, value in opts:
        if opt == '-h':
            help_infos()
        elif opt in ('-c', '--config'):
            conf_file = value

    if not path.exists(conf_file):
        print('Missing configuration file')
        sys.exit(1)

    # load config
    try:
        config = configparser.ConfigParser()
        config.read(conf_file)
    except:
        print('Invalid configuration file')
        sys.exit(1)

    # init logging
    log_file = config.get('server', 'log_file', fallback = '')
    if len(log_file) > 0:
        try:
            with open(log_file, 'w') as f:
                f.close()
        except:
            print('Can not create the log file: {}'.format(log_file))
        if not path.exists(log_file):
            log_file = None
    logging.basicConfig(level = logging.DEBUG, filename = log_file, format = '%(asctime)s %(message)s', datefmt = '%Y-%m-%d %H:%M:%S')
    logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))

    # start server
    address = config.get('server', 'address', fallback = '0.0.0.0')
    port = config.getint('server', 'port', fallback = 6789)
    logging.info('Serving on {}:{}'.format(address, port))
    server = HTTPServer((address, port), RequestHandler)
    server.serve_forever()

if __name__ == '__main__':
    main(sys.argv[1:])
