"""A minimal web micro-framework tailored for tests without external deps."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple
from urllib.parse import parse_qs
from wsgiref.simple_server import make_server


_current_request: "Request" | None = None
_current_session: Dict[str, Any] | None = None


class Request:
    """Lightweight representation of an HTTP request."""

    def __init__(self, method: str, path: str, form: Optional[Dict[str, Any]] = None) -> None:
        self.method = method
        self.path = path
        self.form = form or {}


class _RequestProxy:
    def __getattr__(self, name: str) -> Any:
        if _current_request is None:
            raise RuntimeError("request outside of application context")
        return getattr(_current_request, name)


class _SessionProxy:
    def __getitem__(self, key: str) -> Any:
        if _current_session is None:
            raise RuntimeError("session outside of application context")
        return _current_session[key]

    def __setitem__(self, key: str, value: Any) -> None:
        if _current_session is None:
            raise RuntimeError("session outside of application context")
        _current_session[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        if _current_session is None:
            raise RuntimeError("session outside of application context")
        return _current_session.get(key, default)

    def pop(self, key: str, default: Any = None) -> Any:
        if _current_session is None:
            raise RuntimeError("session outside of application context")
        return _current_session.pop(key, default)

    def clear(self) -> None:
        if _current_session is None:
            raise RuntimeError("session outside of application context")
        _current_session.clear()

    def __contains__(self, key: object) -> bool:
        if _current_session is None:
            raise RuntimeError("session outside of application context")
        return key in _current_session


request = _RequestProxy()
session = _SessionProxy()


@dataclass
class _Route:
    method: str
    rule: str
    func: Callable[..., Any]


class Response:
    """Simple response object compatible with the unit tests."""

    def __init__(self, body: str = "", status_code: int = 200, headers: Optional[Dict[str, str]] = None):
        self.body = body
        self.status_code = status_code
        self.headers: Dict[str, str] = headers or {}

    def get_data(self, as_text: bool = False) -> str | bytes:
        if as_text:
            return self.body
        return self.body.encode("utf-8")


_STATUS_TEXT = {
    200: "200 OK",
    302: "302 Found",
    303: "303 See Other",
    307: "307 Temporary Redirect",
    308: "308 Permanent Redirect",
    400: "400 Bad Request",
    404: "404 Not Found",
}


class MiniApp:
    """Very small Flask-like application for a deterministic WAP workflow."""

    def __init__(self, name: str):
        self.name = name
        self.config: Dict[str, Any] = {}
        self._routes: List[_Route] = []
        self._endpoints: Dict[str, str] = {}

    # ------------------------------------------------------------------ routing helpers
    def route(self, rule: str, methods: Iterable[str] = ("GET",)) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            endpoint = func.__name__
            self._endpoints[endpoint] = rule
            for method in methods:
                self._routes.append(_Route(method.upper(), rule, func))
            return func

        return decorator

    def get(self, rule: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        return self.route(rule, ("GET",))

    def post(self, rule: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        return self.route(rule, ("POST",))

    # ------------------------------------------------------------------ testing helpers
    def test_client(self) -> "TestClient":
        return TestClient(self)

    # ------------------------------------------------------------------ response helpers
    def make_response(self, body: str, status: int = 200, headers: Optional[Dict[str, str]] = None) -> Response:
        return Response(body=body, status_code=status, headers=headers)

    def url_for(self, endpoint: str, **params: Any) -> str:
        rule = self._endpoints.get(endpoint)
        if rule is None:
            raise KeyError(f"Unknown endpoint '{endpoint}'")
        path = rule
        for key, value in params.items():
            placeholder = f"<{key}>"
            if placeholder not in path:
                raise KeyError(f"Parameter '{key}' not part of rule '{rule}'")
            path = path.replace(placeholder, str(value))
        if "<" in path:
            missing = [seg for seg in path.split("<") if ">" in seg]
            raise KeyError(f"Missing parameters for rule '{rule}': {missing}")
        return path

    # ------------------------------------------------------------------ WSGI serving
    def wsgi_app(self, environ: Dict[str, Any], start_response: Callable[..., Any]) -> Any:
        method = environ.get("REQUEST_METHOD", "GET").upper()
        path = environ.get("PATH_INFO", "") or "/"
        data: Dict[str, Any] = {}
        if method == "POST":
            length_str = environ.get("CONTENT_LENGTH") or "0"
            try:
                length = int(length_str)
            except ValueError:
                length = 0
            raw = environ["wsgi.input"].read(length).decode("utf-8")
            parsed = parse_qs(raw)
            data = {key: values[-1] for key, values in parsed.items()}
        response = self._handle_request(method, path, data, {})
        status = _STATUS_TEXT.get(response.status_code, f"{response.status_code} OK")
        headers = list(response.headers.items())
        headers.append(("Content-Type", "text/html; charset=utf-8"))
        start_response(status, headers)
        yield response.get_data(as_text=False)

    def serve(self, host: str = "127.0.0.1", port: int = 5000) -> None:
        with make_server(host, port, self.wsgi_app) as server:
            print(f"Serving on http://{host}:{port}")
            server.serve_forever()

    # ------------------------------------------------------------------ internal dispatching
    def _handle_request(
        self,
        method: str,
        path: str,
        data: Optional[Dict[str, Any]],
        session_store: Dict[str, Any],
    ) -> Response:
        route, params = self._match_route(method, path)
        if route is None:
            return Response("Страница не найдена", status_code=404)

        global _current_request, _current_session
        previous_request, previous_session = _current_request, _current_session
        request_obj = Request(method, path, form=data)
        _current_request = request_obj
        _current_session = session_store
        try:
            result = route.func(**params)
        finally:
            _current_request = previous_request
            _current_session = previous_session

        return self._normalise_response(result)

    def _match_route(self, method: str, path: str) -> Tuple[Optional[_Route], Dict[str, str]]:
        for route in self._routes:
            if route.method != method.upper():
                continue
            params = _match_path(route.rule, path)
            if params is not None:
                return route, params
        return None, {}

    def _normalise_response(self, result: Any) -> Response:
        if isinstance(result, Response):
            return result
        if isinstance(result, tuple):
            body = result[0] if len(result) > 0 else ""
            status = result[1] if len(result) > 1 else 200
            headers = result[2] if len(result) > 2 else None
            return Response(str(body), status_code=status, headers=headers)
        if result is None:
            return Response("", status_code=204)
        return Response(str(result))


class TestClient:
    """Simple test client replicating the parts of Flask used in tests."""

    def __init__(self, app: MiniApp):
        self.app = app
        self._session: Dict[str, Any] = {}

    def _request(
        self, method: str, path: str, data: Optional[Dict[str, Any]] = None, follow_redirects: bool = False
    ) -> Response:
        response = self.app._handle_request(method, path, data or {}, self._session)
        while follow_redirects and response.status_code in {301, 302, 303, 307, 308}:
            location = response.headers.get("Location")
            if not location:
                break
            response = self.app._handle_request("GET", location, {}, self._session)
        return response

    def post(self, path: str, data: Optional[Dict[str, Any]] = None, follow_redirects: bool = False) -> Response:
        return self._request("POST", path, data=data, follow_redirects=follow_redirects)

    def get(self, path: str, follow_redirects: bool = False) -> Response:
        return self._request("GET", path, data={}, follow_redirects=follow_redirects)


def _match_path(rule: str, path: str) -> Optional[Dict[str, str]]:
    rule_parts = [part for part in rule.strip("/").split("/") if part]
    path_parts = [part for part in path.strip("/").split("/") if part]
    if not rule_parts and not path_parts:
        return {}
    if len(rule_parts) != len(path_parts):
        return None
    params: Dict[str, str] = {}
    for rule_part, path_part in zip(rule_parts, path_parts):
        if rule_part.startswith("<") and rule_part.endswith(">"):
            params[rule_part[1:-1]] = path_part
        elif rule_part != path_part:
            return None
    return params


def flash(message: str) -> None:
    if _current_session is None:
        return
    flashes = _current_session.setdefault("_flashes", [])
    flashes.append(str(message))


def pop_flashes() -> List[str]:
    if _current_session is None:
        return []
    return _current_session.pop("_flashes", [])


def redirect(location: str, status: int = 302) -> Response:
    return Response("", status_code=status, headers={"Location": location})


__all__ = [
    "MiniApp",
    "Response",
    "request",
    "session",
    "flash",
    "pop_flashes",
    "redirect",
]
