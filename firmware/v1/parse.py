"""Parse (absolute and relative) URLs.

urlparse module is based upon the following RFC specifications.

RFC 3986 (STD66): "Uniform Resource Identifiers" by T. Berners-Lee, R. Fielding
and L.  Masinter, January 2005.

RFC 2732 : "Format for Literal IPv6 Addresses in URL's by R.Hinden, B.Carpenter
and L.Masinter, December 1999.

RFC 2396:  "Uniform Resource Identifiers (URI)": Generic Syntax by T.
Berners-Lee, R. Fielding, and L. Masinter, August 1998.

RFC 2368: "The mailto URL scheme", by P.Hoffman , L Masinter, J. Zawinski, July 1998.

RFC 1808: "Relative Uniform Resource Locators", by R. Fielding, UC Irvine, June
1995.

RFC 1738: "Uniform Resource Locators (URL)" by T. Berners-Lee, L. Masinter, M.
McCahill, December 1994

RFC 3986 is considered the current standard and any future changes to
urlparse module should conform with it.  The urlparse module is
currently not entirely compliant with this RFC due to defacto
scenarios for parsing, and for backward compatibility purposes, some
parsing quirks from older RFCs are retained. The testcases in
test_urlparse.py provides a good indicator of parsing behavior.
"""

import re

__all__ = [
    "urlparse",
    "urlunparse",
    "urlsplit",
    "urlunsplit",
    "parse_qsl",
    "unquote",
    "unquote_plus",
    "unquote_to_bytes",
]

# A classification of schemes ('' means apply by default)
uses_relative = [
    "ftp",
    "http",
    "gopher",
    "nntp",
    "imap",
    "wais",
    "file",
    "https",
    "shttp",
    "mms",
    "prospero",
    "rtsp",
    "rtspu",
    "",
    "sftp",
    "svn",
    "svn+ssh",
]
uses_netloc = [
    "ftp",
    "http",
    "gopher",
    "nntp",
    "telnet",
    "imap",
    "wais",
    "file",
    "mms",
    "https",
    "shttp",
    "snews",
    "prospero",
    "rtsp",
    "rtspu",
    "rsync",
    "",
    "svn",
    "svn+ssh",
    "sftp",
    "nfs",
    "git",
    "git+ssh",
]
uses_params = [
    "ftp",
    "hdl",
    "prospero",
    "http",
    "imap",
    "https",
    "shttp",
    "rtsp",
    "rtspu",
    "sip",
    "sips",
    "mms",
    "",
    "sftp",
    "tel",
]

# These are not actually used anymore, but should stay for backwards
# compatibility.  (They are undocumented, but have a public-looking name.)
non_hierarchical = [
    "gopher",
    "hdl",
    "mailto",
    "news",
    "telnet",
    "wais",
    "imap",
    "snews",
    "sip",
    "sips",
]
uses_query = [
    "http",
    "wais",
    "imap",
    "https",
    "shttp",
    "mms",
    "gopher",
    "rtsp",
    "rtspu",
    "sip",
    "sips",
    "",
]
uses_fragment = [
    "ftp",
    "hdl",
    "http",
    "gopher",
    "news",
    "nntp",
    "wais",
    "https",
    "shttp",
    "snews",
    "file",
    "prospero",
    "",
]

# Characters valid in scheme names
scheme_chars = "abcdefghijklmnopqrstuvwxyz" "ABCDEFGHIJKLMNOPQRSTUVWXYZ" "0123456789" "+-."

# XXX: Consider replacing with functools.lru_cache
MAX_CACHE_SIZE = 20
_parse_cache = {}


def clear_cache():
    """Clear the parse cache and the quoters cache."""
    _parse_cache.clear()


# Helpers for bytes handling
# For 3.2, we deliberately require applications that
# handle improperly quoted URLs to do their own
# decoding and encoding. If valid use cases are
# presented, we may relax this by using latin-1
# decoding internally for 3.3
_implicit_encoding = "ascii"
_implicit_errors = "strict"


def _noop(obj):
    return obj


def _encode_result(obj, encoding=_implicit_encoding, errors=_implicit_errors):
    return obj.encode(encoding, errors)


def _decode_args(args, encoding=_implicit_encoding, errors=_implicit_errors):
    return tuple(x.decode(encoding, errors) if x else "" for x in args)


def _coerce_args(*args):
    # Invokes decode if necessary to create str args
    # and returns the coerced inputs along with
    # an appropriate result coercion function
    #   - noop for str inputs
    #   - encoding function otherwise
    str_input = isinstance(args[0], str)
    for arg in args[1:]:
        # We special-case the empty string to support the
        # "scheme=''" default argument to some functions
        if arg and isinstance(arg, str) != str_input:
            raise TypeError("Cannot mix str and non-str arguments")
    if str_input:
        return args + (_noop,)
    return _decode_args(args) + (_encode_result,)


# Result objects are more helpful than simple tuples
class _ResultMixinStr(object):
    """Standard approach to encoding parsed results from str to bytes"""

    __slots__ = ()

    def encode(self, encoding="ascii", errors="strict"):
        return self._encoded_counterpart(*(x.encode(encoding, errors) for x in self))


class _ResultMixinBytes(object):
    """Standard approach to decoding parsed results from bytes to str"""

    __slots__ = ()

    def decode(self, encoding="ascii", errors="strict"):
        return self._decoded_counterpart(*(x.decode(encoding, errors) for x in self))


class _NetlocResultMixinBase(object):
    """Shared methods for the parsed result objects containing a netloc element"""

    __slots__ = ()

    @property
    def username(self):
        return self._userinfo[0]

    @property
    def password(self):
        return self._userinfo[1]

    @property
    def hostname(self):
        hostname = self._hostinfo[0]
        if not hostname:
            hostname = None
        elif hostname is not None:
            hostname = hostname.lower()
        return hostname

    @property
    def port(self):
        port = self._hostinfo[1]
        if port is not None:
            port = int(port, 10)
            # Return None on an illegal port
            if not (0 <= port <= 65535):
                return None
        return port


class _NetlocResultMixinStr(_NetlocResultMixinBase, _ResultMixinStr):
    __slots__ = ()

    @property
    def _userinfo(self):
        netloc = self.netloc
        userinfo, have_info, hostinfo = netloc.rpartition("@")
        if have_info:
            username, have_password, password = userinfo.partition(":")
            if not have_password:
                password = None
        else:
            username = password = None
        return username, password

    @property
    def _hostinfo(self):
        netloc = self.netloc
        _, _, hostinfo = netloc.rpartition("@")
        _, have_open_br, bracketed = hostinfo.partition("[")
        if have_open_br:
            hostname, _, port = bracketed.partition("]")
            _, have_port, port = port.partition(":")
        else:
            hostname, have_port, port = hostinfo.partition(":")
        if not have_port:
            port = None
        return hostname, port


class _NetlocResultMixinBytes(_NetlocResultMixinBase, _ResultMixinBytes):
    __slots__ = ()

    @property
    def _userinfo(self):
        netloc = self.netloc
        userinfo, have_info, hostinfo = netloc.rpartition(b"@")
        if have_info:
            username, have_password, password = userinfo.partition(b":")
            if not have_password:
                password = None
        else:
            username = password = None
        return username, password

    @property
    def _hostinfo(self):
        netloc = self.netloc
        _, _, hostinfo = netloc.rpartition(b"@")
        _, have_open_br, bracketed = hostinfo.partition(b"[")
        if have_open_br:
            hostname, _, port = bracketed.partition(b"]")
            _, have_port, port = port.partition(b":")
        else:
            hostname, have_port, port = hostinfo.partition(b":")
        if not have_port:
            port = None
        return hostname, port


from collections import namedtuple

_DefragResultBase = namedtuple("DefragResult", "url fragment")
_SplitResultBase = namedtuple("SplitResult", "scheme netloc path query fragment")
_ParseResultBase = namedtuple("ParseResult", "scheme netloc path params query fragment")

# For backwards compatibility, alias _NetlocResultMixinStr
# ResultBase is no longer part of the documented API, but it is
# retained since deprecating it isn't worth the hassle
ResultBase = _NetlocResultMixinStr

# Structured result objects for string data
class DefragResult(_DefragResultBase, _ResultMixinStr):
    __slots__ = ()

    def geturl(self):
        if self.fragment:
            return self.url + "#" + self.fragment
        else:
            return self.url


class SplitResult(_SplitResultBase, _NetlocResultMixinStr):
    __slots__ = ()

    def geturl(self):
        return urlunsplit(self)


class ParseResult(_ParseResultBase, _NetlocResultMixinStr):
    __slots__ = ()

    def geturl(self):
        return urlunparse(self)


# Structured result objects for bytes data
class DefragResultBytes(_DefragResultBase, _ResultMixinBytes):
    __slots__ = ()

    def geturl(self):
        if self.fragment:
            return self.url + b"#" + self.fragment
        else:
            return self.url


class SplitResultBytes(_SplitResultBase, _NetlocResultMixinBytes):
    __slots__ = ()

    def geturl(self):
        return urlunsplit(self)


class ParseResultBytes(_ParseResultBase, _NetlocResultMixinBytes):
    __slots__ = ()

    def geturl(self):
        return urlunparse(self)


# Set up the encode/decode result pairs
def _fix_result_transcoding():
    _result_pairs = (
        (DefragResult, DefragResultBytes),
        (SplitResult, SplitResultBytes),
        (ParseResult, ParseResultBytes),
    )
    for _decoded, _encoded in _result_pairs:
        _decoded._encoded_counterpart = _encoded
        _encoded._decoded_counterpart = _decoded


_fix_result_transcoding()
del _fix_result_transcoding


def urlparse(url, scheme="", allow_fragments=True):
    """Parse a URL into 6 components:
    <scheme>://<netloc>/<path>;<params>?<query>#<fragment>
    Return a 6-tuple: (scheme, netloc, path, params, query, fragment).
    Note that we don't break the components up in smaller bits
    (e.g. netloc is a single string) and we don't expand % escapes."""
    url, scheme, _coerce_result = _coerce_args(url, scheme)
    splitresult = urlsplit(url, scheme, allow_fragments)
    scheme, netloc, url, query, fragment = splitresult
    if scheme in uses_params and ";" in url:
        url, params = _splitparams(url)
    else:
        params = ""
    result = ParseResult(scheme, netloc, url, params, query, fragment)
    return _coerce_result(result)


def _splitparams(url):
    if "/" in url:
        i = url.find(";", url.rfind("/"))
        if i < 0:
            return url, ""
    else:
        i = url.find(";")
    return url[:i], url[i + 1 :]


def _splitnetloc(url, start=0):
    delim = len(url)  # position of end of domain part of url, default is end
    for c in "/?#":  # look for delimiters; the order is NOT important
        wdelim = url.find(c, start)  # find first of this delim
        if wdelim >= 0:  # if found
            delim = min(delim, wdelim)  # use earliest delim position
    return url[start:delim], url[delim:]  # return (domain, rest)


def urlsplit(url, scheme="", allow_fragments=True):
    """Parse a URL into 5 components:
    <scheme>://<netloc>/<path>?<query>#<fragment>
    Return a 5-tuple: (scheme, netloc, path, query, fragment).
    Note that we don't break the components up in smaller bits
    (e.g. netloc is a single string) and we don't expand % escapes."""
    url, scheme, _coerce_result = _coerce_args(url, scheme)
    allow_fragments = bool(allow_fragments)
    key = url, scheme, allow_fragments, type(url), type(scheme)
    cached = _parse_cache.get(key, None)
    if cached:
        return _coerce_result(cached)
    if len(_parse_cache) >= MAX_CACHE_SIZE:  # avoid runaway growth
        clear_cache()
    netloc = query = fragment = ""
    i = url.find(":")
    if i > 0:
        if url[:i] == "http":  # optimize the common case
            scheme = url[:i].lower()
            url = url[i + 1 :]
            if url[:2] == "//":
                netloc, url = _splitnetloc(url, 2)
                if ("[" in netloc and "]" not in netloc) or ("]" in netloc and "[" not in netloc):
                    raise ValueError("Invalid IPv6 URL")
            if allow_fragments and "#" in url:
                url, fragment = url.split("#", 1)
            if "?" in url:
                url, query = url.split("?", 1)
            v = SplitResult(scheme, netloc, url, query, fragment)
            _parse_cache[key] = v
            return _coerce_result(v)
        for c in url[:i]:
            if c not in scheme_chars:
                break
        else:
            # make sure "url" is not actually a port number (in which case
            # "scheme" is really part of the path)
            rest = url[i + 1 :]
            if not rest or any(c not in "0123456789" for c in rest):
                # not a port number
                scheme, url = url[:i].lower(), rest

    if url[:2] == "//":
        netloc, url = _splitnetloc(url, 2)
        if ("[" in netloc and "]" not in netloc) or ("]" in netloc and "[" not in netloc):
            raise ValueError("Invalid IPv6 URL")
    if allow_fragments and "#" in url:
        url, fragment = url.split("#", 1)
    if "?" in url:
        url, query = url.split("?", 1)
    v = SplitResult(scheme, netloc, url, query, fragment)
    _parse_cache[key] = v
    return _coerce_result(v)


def urlunparse(components):
    """Put a parsed URL back together again.  This may result in a
    slightly different, but equivalent URL, if the URL that was parsed
    originally had redundant delimiters, e.g. a ? with an empty query
    (the draft states that these are equivalent)."""
    scheme, netloc, url, params, query, fragment, _coerce_result = _coerce_args(*components)
    if params:
        url = "%s;%s" % (url, params)
    return _coerce_result(urlunsplit((scheme, netloc, url, query, fragment)))


def urlunsplit(components):
    """Combine the elements of a tuple as returned by urlsplit() into a
    complete URL as a string. The data argument can be any five-item iterable.
    This may result in a slightly different, but equivalent URL, if the URL that
    was parsed originally had unnecessary delimiters (for example, a ? with an
    empty query; the RFC states that these are equivalent)."""
    scheme, netloc, url, query, fragment, _coerce_result = _coerce_args(*components)
    if netloc or (scheme and scheme in uses_netloc and url[:2] != "//"):
        if url and url[:1] != "/":
            url = "/" + url
        url = "//" + (netloc or "") + url
    if scheme:
        url = scheme + ":" + url
    if query:
        url = url + "?" + query
    if fragment:
        url = url + "#" + fragment
    return _coerce_result(url)


_hexdig = "0123456789ABCDEFabcdef"
_hextobyte = {(a + b).encode(): bytes([int(a + b, 16)]) for a in _hexdig for b in _hexdig}


def unquote_to_bytes(string):
    """unquote_to_bytes('abc%20def') -> b'abc def'."""
    # Note: strings are encoded as UTF-8. This is only an issue if it contains
    # unescaped non-ASCII characters, which URIs should not.
    if not string:
        # Is it a string-like object?
        string.split
        return b""
    if isinstance(string, str):
        string = string.encode("utf-8")
    bits = string.split(b"%")
    if len(bits) == 1:
        return string
    res = [bits[0]]
    append = res.append
    for item in bits[1:]:
        try:
            append(_hextobyte[item[:2]])
            append(item[2:])
        except KeyError:
            append(b"%")
            append(item)
    return b"".join(res)


_asciire = re.compile(r"([\x00-\x7f]+)")


def unquote(string, encoding="utf-8", errors="replace"):
    """Replace %xx escapes by their single-character equivalent. The optional
    encoding and errors parameters specify how to decode percent-encoded
    sequences into Unicode characters, as accepted by the bytes.decode()
    method.
    By default, percent-encoded sequences are decoded with UTF-8, and invalid
    sequences are replaced by a placeholder character.

    unquote('abc%20def') -> 'abc def'.
    """
    if "%" not in string:
        string.split
        return string
    if encoding is None:
        encoding = "utf-8"
    if errors is None:
        errors = "replace"
    res = unquote_to_bytes(string).decode(encoding, errors)
    return res


def unquote_plus(string, encoding="utf-8", errors="replace"):
    """Like unquote(), but also replace plus signs by spaces, as required for
    unquoting HTML form values.

    unquote_plus('%7e/abc+def') -> '~/abc def'
    """
    string = string.replace("+", " ")
    return unquote(string, encoding, errors)


_ALWAYS_SAFE = frozenset(
    b"ABCDEFGHIJKLMNOPQRSTUVWXYZ" b"abcdefghijklmnopqrstuvwxyz" b"0123456789" b"_.-"
)
