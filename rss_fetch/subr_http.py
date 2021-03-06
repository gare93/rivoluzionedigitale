# rss_fetch/subr_http.py

#
# Copyright (c) 2013 Simone Basso <bassosimone@gmail.com>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
#

""" HTTP subroutines """

import httplib
import logging
import sys
import urlparse

MAXBODY = 1 << 22
MAXPIECE = 1 << 16

CONNECTIONS = {
}

def connect(site, secure=0):
    """ Connect to site """
    tpl = (secure, site)
    if tpl not in CONNECTIONS:
        if secure:
            connection = httplib.HTTPSConnection(site)
        else:
            connection = httplib.HTTPConnection(site)

        return connection  # FIXME

#       CONNECTIONS[tpl] = connection
#   connection = CONNECTIONS[tpl]
#   return connection

def fetch_url(url, secure=0, noisy=0):
    """ Fetch the given URL """
    parsed = urlparse.urlsplit(url)
    return fetch(parsed[1], parsed[2], noisy)

def fetch(site, path, secure=0, noisy=0):
    """ Fetch path from site """

    cnt = 10
    while cnt > 0:
        logging.info("subr_http: GET %s from %s (#redirs: %d, secure: %d)",
                     path, site, cnt, secure)

        connection = connect(site, secure)
        #connection.set_debuglevel(noisy)
        connection.putrequest("GET", path)
        connection.endheaders()
        response = connection.getresponse()

        maxbody = MAXBODY
        vector = []
        while maxbody >= 0:
            piece = response.read(MAXPIECE)
            if not piece:
                break
            vector.append(piece)
            maxbody -= len(piece)
        if maxbody < 0:
            # Note: disconnect unavoidable because we don't read the whole body
            disconnect(site, secure)
            logging.warning("subr_http: body too large")
            return

        if response.getheader("Connection") == "close":
            logging.info("subr_http: disconnecting on server request")
            disconnect(site, secure)

        if response.status == 301 or response.status == 302:
            cnt -= 1
            location = response.getheader("Location")
            if not location:
                logging.warning("subr_http: missing location header")
                return
            logging.info("subr_http: redirected to %s", location)
            parsed = urlparse.urlsplit(location)
            secure = (parsed[0] == "https")
            if parsed[1]:
                site = parsed[1]
            if parsed[2]:
                path = parsed[2]
            continue

        if response.status != 200:
            logging.warning("subr_http: bad status: %d", response.status)
            return

        body = "".join(vector)
        logging.info("subr_http: %s from %s is %d bytes", path, site, len(body))
        return response, body

    logging.warning("subr_http: too many redirections")

def disconnect(site, secure=0):
    """ Disconnect from site """
    #del CONNECTIONS[(secure, site)]  # FIXME

def parse_content_type(ctype):
    """ Parse Content-Type header value """
    index = ctype.find(";")
    if index >= 0:
        encoding = ctype[index + 1:].strip()
        encoding = encoding.replace("charset=", "")
        ctype = ctype[:index].strip()
    else:
        encoding = None
    return ctype, encoding

if __name__ == "__main__":
    logging.getLogger().setLevel(logging.DEBUG)
    if len(sys.argv) == 3:
        fetch(sys.argv[1], sys.argv[2], noisy=1)
        sys.exit(0)
    if len(sys.argv) == 2:
        fetch_url(sys.argv[1], noisy=1)
        sys.exit(0)
    sys.stderr.write("usage: subr_http site path\n")
    sys.stderr.write("       subr_http url\n")
    sys.exit(1)
