# Copyright (c) 2013 Alon Swartz <alon@turnkeylinux.org>
#
# This file is part of OctoHub.
#
# OctoHub is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software
# Foundation; either version 3 of the License, or (at your option) any later
# version.

import re

from octohub.utils import AttrDict, get_logger
from octohub.exceptions import ResponseError, OctoHubError

log = get_logger('response')

def _get_content_type(response):
    """Parse response and return content-type"""
    try:
        content_type = response.headers['Content-Type']
        content_type = content_type.split(';', 1)[0]
    except KeyError:
        content_type = None

    return content_type

def _parse_link(header_link):
    """Parse header link and return AttrDict[rel].uri|params"""
    links = AttrDict()
    for s in header_link.split(','):
        link = AttrDict()

        m = re.match('<(.*)\?(.*)>', s.split(';')[0].strip())
        link.uri = m.groups()[0]
        link.params = {}
        for kv in m.groups()[1].split('&'):
            key, value = kv.split('=')
            link.params[key] = value

        m = re.match('rel="(.*)"', s.split(';')[1].strip())
        rel = m.groups()[0]

        links[rel] = link
        log.debug('link-{0!s}-page: {1!s}'.format(rel, link.params['page']))

    return links

def parse_element(el):
    """Parse el recursively, replacing dicts with AttrDicts representation"""
    if type(el) == dict:
        el_dict = AttrDict()
        for key, val in el.items():
            el_dict[key] = parse_element(val)

        return el_dict

    elif type(el) == list:
        el_list = []
        for l in el:
            el_list.append(parse_element(l))

        return el_list

    else:
        return el

def parse_response(response):
    """Parse request response object and raise exception on response error code
        response (requests.Response object):

        returns: requests.Response object, including:
            response.parsed (AttrDict)
            response.parsed_link (AttrDict)
            http://docs.python-requests.org/en/latest/api/#requests.Response
    """
    response.parsed = AttrDict()
    response.parsed_link = AttrDict()

    if 'link' in response.headers.keys():
        response.parsed_link = _parse_link(response.headers['link'])

    headers = ['status', 'x-ratelimit-limit', 'x-ratelimit-remaining']
    for header in headers:
        if header in response.headers.keys():
            log.info('{0!s}: {1!s}'.format(header, response.headers[header]))

    content_type = _get_content_type(response)

    if content_type == 'application/json':
        json = response.json
        if callable(json):
            json = json()
        response.parsed = parse_element(json)
    else:
        if not response.status_code == 204:
            raise OctoHubError('unhandled content_type: {0!s}'.format(content_type))

    if not response.status_code in (200, 201, 204):
        raise ResponseError(response.parsed)

    return response


