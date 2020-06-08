#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import time
import base64
import hashlib
import hmac
import json
import configparser
import logging
import subprocess
import sys
import getopt
from os import path
from urllib.parse import parse_qs, urlparse
from http.server import BaseHTTPRequestHandler, HTTPServer

class RequestHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        '''does not handle the GET requests, direct response 403.'''
        self.send_error(403, 'Forbidden')

    def do_POST(self):
        '''handling the POST requests.'''
        global config
        user_agent = self.headers.get('User-Agent').lower()
        content_len = int(self.headers.get('Content-Length', 0))
        content_type = self.headers.get('Content-Type').lower()
        payload = self.rfile.read(content_len)

        # check request content type
        try:
            if content_type == 'application/x-www-form-urlencoded':
                data = parse_qs(str(payload, encoding = 'utf-8'), keep_blank_values = 1)
                data = json.loads(data['payload'][0])
            elif content_type == 'application/json':
                data = json.loads(payload)
            else:
                logging.warning('Invalid content-type: {}'.format(content_type))
                self.send_error(400)
                return
        except:
            logging.warning('Invalid request data')
            self.send_error(400)
            return

        # for Github
        if user_agent.find('github-hookshot') != -1 and config.getboolean('github', 'verify', fallback = False):
            # check signature
            request_signature = self.headers.get('X-Hub-Signature')
            if request_signature == None:
                logging.warning('Missing Signature')
                self.send_error(401)
                return

            secret = bytes(config.get('github', 'secret'), encoding = 'utf-8')
            verify_signature = 'sha1=' + hmac.new(secret, payload, hashlib.sha1).hexdigest()
            if request_signature != verify_signature:
                logging.warning('Invalid Signature')
                self.send_error(401)
                return
        # for Gitee
        elif user_agent == 'git-oschina-hook' and config.getboolean('gitee', 'verify', fallback = False):
            query = parse_qs(urlparse(self.path).query)
            request_signature = self.headers.get('X-Gitee-Token')
            secret = config.get('gitee', 'secret')
            # check signature
            if request_signature == None:
                logging.warning('Missing Signature or Password')
                self.send_error(401)
                return
            if 'sign' in query:
                timestamp = int(self.headers.get('X-Gitee-Timestamp'))
                secret_enc = bytes(secret, encoding = 'utf-8')
                str_to_sign = '{}\n{}'.format(timestamp, secret)
                str_to_sign_enc = bytes(str_to_sign, encoding = 'utf-8')
                verify_signature = base64.b64encode(hmac.new(secret_enc, str_to_sign_enc, digestmod=hashlib.sha256).digest())
                if bytes(request_signature, encoding = 'utf-8') != verify_signature:
                    logging.warning('Invalid Signature')
                    self.send_error(401)
                    return
            # check password
            elif request_signature != secret:
                logging.warning('Invalid Password')
                self.send_error(401)
                return
        # custom sender
        elif user_agent == config.get('custom', 'user_agent', fallback = ''):
            self.send_error(412)
            return
        # unknow sender
        else:
            logging.warning('Invalid sender: {}'.format(user_agent))
            self.send_error(412)
            return
        # check repository info
        if 'repository' in data:
            repo = data['repository']['full_name']
            if repo in config:
                cwd = config.get(repo, 'cwd')
                cmd = config.get(repo, 'cmd')
                logging.info('[{}] Execute: {}'.format(repo, cmd))
                process = subprocess.Popen(cmd,
                    cwd = cwd,
                    shell = True,
                    stdout = subprocess.PIPE,
                    stderr = subprocess.PIPE)
                for line in process.stdout:
                    logging.info('[{}] Output: {}'.format(repo, str(line.rstrip(), encoding = 'utf-8')))
            else:
                logging.warning('No repository settings for "{}".'.format(repo))

            # successful
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'OK')
        else:
            logging.warning('Missing repository: "{}".'.format(repo))
            self.send_error(404)

def help_infos():
    '''Print help infos'''
    print('usage: webhooks.py -c <configuration_file>')
    sys.exit(0)

if __name__ == '__main__':
    global config
    # default configuration file
    conf_file = '/usr/local/etc/webhooks.ini'
    # handle arguments
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'hc:', ['config='])
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
    server = HTTPServer((address, port), RequestHandler)
    server.serve_forever()
