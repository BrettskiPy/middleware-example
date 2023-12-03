from typing import Union, cast

from asgiref.typing import (
    ASGI3Application,
    ASGIReceiveCallable,
    ASGISendCallable,
    HTTPScope,
    Scope,
    WebSocketScope,
)
from black import re

from typing import Any, Callable, Optional, Sequence, Type, Union

from fastapi import APIRouter, params, FastAPI
from fastapi.datastructures import Default
from fastapi.types import DecoratedCallable

from starlette.responses import JSONResponse, Response, PlainTextResponse
from starlette.routing import BaseRoute, Match
from starlette.types import ASGIApp, Receive, Scope, Send
from starlette.exceptions import HTTPException
from fastapi.routing import APIRoute


class AcceptHeaderVersionMiddleware:
    """
    Use this middleware to parse the Accept Header if present and get an API version
    from the vendor tree. See https://www.rfc-editor.org/rfc/rfc6838#section-3.2

    If incoming http or websocket request contains an Accept header with the following
    value: `"accept/vnd.vendor_prefix.v42+json"`, the scope of the ASGI application
    will then contain an `api_version` of 42.

    If the http or websocket request does not contain an Accept header, or if the accept
    header value does not use a proper format, the scope of the ASGI application will
    then contain an `api_version` that defaults to the provided `latest_version`
    """

    def __init__(
        self, app: ASGI3Application, vendor_prefix: str, latest_version: str
    ) -> None:
        self.app = app
        self.latest_version = latest_version
        self.accept_regex = rf"^application/vnd\.{vendor_prefix}\.v([0-9]+)\+.*"

    async def __call__(
        self, scope: Scope, receive: ASGIReceiveCallable, send: ASGISendCallable
    ) -> None:
        if scope["type"] in ("http", "websocket"):
            scope = cast(Union[HTTPScope, WebSocketScope], scope)
            headers = dict(scope["headers"])
            scope["latest_version"] = self.latest_version  # type: ignore[index]
            scope["requested_version"] = self.latest_version  # type: ignore[index]

            if b"accept" in headers:
                accept_header = headers[b"accept"].decode("latin1")
                match = re.search(self.accept_regex, accept_header)
                if match is not None:
                    api_version = match.group(1)
                    if api_version is not None:
                        scope["requested_version"] = api_version  # type: ignore[index]

        return await self.app(scope, receive, send)


class VersionedAPIRoute(APIRoute):
    @property
    def endpoint_version(self) -> str:
        return str(self.endpoint.__api_version__)  # type:ignore

    def is_version_matching(self, scope: Scope) -> bool:
        requested_version = scope["requested_version"]
        is_latest = self.endpoint_version == "latest"

        return (
            is_latest and requested_version == scope["latest_version"]
        ) or self.endpoint_version == requested_version

    def matches(self, scope: Scope) -> tuple[Match, Scope]:
        match, child_scope = super().matches(scope)

        if match == Match.NONE or match == Match.PARTIAL:
            return match, child_scope
        if self.is_version_matching(scope):
            return Match.FULL, child_scope
        else:
            return Match.PARTIAL, child_scope

    async def handle(self, scope: Scope, receive: Receive, send: Send) -> None:
        if not self.is_version_matching(scope):
            if "app" in scope:
                raise HTTPException(
                    406,
                    f"Requested version {scope['requested_version']} does not exist. "
                    f"Latest available version is {scope['latest_version']}.",
                )
            else:
                response = PlainTextResponse("Not Acceptable", status_code=406)
            await response(scope, receive, send)
        await super().handle(scope, receive, send)


class VersionedAPIRouter(APIRouter):
    def __init__(
        self,
        *,
        prefix: str = "",
        tags: Optional[list[str]] = None,
        dependencies: Optional[Sequence[params.Depends]] = None,
        default_response_class: Type[Response] = Default(JSONResponse),
        responses: Optional[dict[Union[int, str], dict[str, Any]]] = None,
        callbacks: Optional[list[BaseRoute]] = None,
        routes: Optional[list[BaseRoute]] = None,
        redirect_slashes: bool = True,
        default: Optional[ASGIApp] = None,
        dependency_overrides_provider: Optional[Any] = None,
        route_class: Type[VersionedAPIRoute] = VersionedAPIRoute,
        on_startup: Optional[Sequence[Callable[[], Any]]] = None,
        on_shutdown: Optional[Sequence[Callable[[], Any]]] = None,
        deprecated: Optional[bool] = None,
        include_in_schema: bool = True,
    ) -> None:
        super().__init__(
            prefix=prefix,
            tags=tags,
            dependencies=dependencies,
            default_response_class=default_response_class,
            responses=responses,
            callbacks=callbacks,
            routes=routes,
            redirect_slashes=redirect_slashes,
            default=default,
            dependency_overrides_provider=dependency_overrides_provider,
            route_class=route_class,
            on_startup=on_startup,
            on_shutdown=on_shutdown,
            deprecated=deprecated,
            include_in_schema=include_in_schema,
        )

    def version(
        self, api_version: str
    ) -> Callable[[DecoratedCallable], DecoratedCallable]:
        def decorator(func: DecoratedCallable) -> DecoratedCallable:
            func.__api_version__ = api_version  # type:ignore
            return func

        return decorator


FOO_V1 = "You reached foo router version 1"
FOO_V2 = "You reached foo router version 2"
FOO_V3 = "You reached foo router version 3"
FOO_LATEST = "This is the latest foo router"

router = VersionedAPIRouter()


@router.get("/foo")
@router.version("1")
async def foo_v1() -> dict:
    return {"Foo Version": FOO_V1}


@router.get("/foo")
@router.version("2")
async def foo_v2() -> dict:
    return {"Foo Version": FOO_V2}


@router.get("/foo")
@router.version("3")
async def foo_v3() -> dict:
    return {"Foo Version": FOO_V3}


@router.get("/foo")
@router.version("latest")
async def foo_latest() -> dict:
    return {"Foo latest": FOO_LATEST}


app = FastAPI(title="Versioned app")
app.add_middleware(
    AcceptHeaderVersionMiddleware, vendor_prefix="mytestapp", latest_version="4"
)
app.include_router(router)
