"""Serve the retained small snapshot for focused CSV/ZIP transport tests.

National browser tests independently exercise the current shared country view.
"""
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote,urlsplit
from flask import Flask,g,render_template

def legacy_server(root):
    app=Flask(__name__,template_folder=str(root/'intelligence/templates'),static_folder=str(root/'intelligence/static'),static_url_path='/static')
    with app.test_request_context('/'):
        g.user={'username':'Transport test','role':'analyst'}
        html=render_template('index.html',sources={},public_snapshot=True).encode()
    class Handler(SimpleHTTPRequestHandler):
        def log_message(self,*args):pass
        def translate_path(self,path):
            path=unquote(urlsplit(path).path)
            for prefix,directory in [('/static/',root/'intelligence/static'),('/data/',root/'deployment/data')]:
                if path.startswith(prefix):
                    target=(directory/path[len(prefix):]).resolve()
                    return str(target) if target.is_relative_to(directory.resolve()) else str(root/'nonexistent')
            return str(root/'nonexistent')
        def do_GET(self):
            if urlsplit(self.path).path=='/':
                self.send_response(200);self.send_header('Content-Type','text/html;charset=utf-8');self.send_header('Content-Length',str(len(html)));self.end_headers();self.wfile.write(html)
            else:super().do_GET()
    return ThreadingHTTPServer(('127.0.0.1',0),Handler)
