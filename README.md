# Versioned API Middleware and Router for FastAPI


## Overview
This implementation provides a versioning system for FastAPI routes using the `Accept` header. It allows clients to request specific versions of an API by including a version number in the `Accept` header. The middleware will parse this header and route the request to the appropriate API version.

This middleware was found here https://github.com/tiangolo/fastapi/issues/3910#issuecomment-1024132161 and is a fantastic example for header version based routing. 

## Features
- **AcceptHeaderVersionMiddleware**: Parses the `Accept` header to extract the API version.
- **VersionedAPIRoute**: Custom API route that matches the requested version.
- **VersionedAPIRouter**: Extension of FastAPI's `APIRouter` to handle versioned routes.

## Usage

### Middleware: AcceptHeaderVersionMiddleware
This middleware checks for an `Accept` header in the incoming HTTP or WebSocket request. If the header is present and formatted correctly, it extracts the API version and includes it in the request scope. 

Example format for the `Accept` header: `application/vnd.mytestapp.v3+json`.

#### Initialization
```python
from fastapi import FastAPI
from your_module import AcceptHeaderVersionMiddleware, VersionedAPIRouter

app = FastAPI(title="Versioned app")

# Add the middleware
app.add_middleware(
    AcceptHeaderVersionMiddleware, 
    vendor_prefix="mytestapp", 
    latest_version="4"
)

# Include the router
app.include_router(router)
```

### Requesting a Specific Version
Clients can request a specific version of an API endpoint by setting the Accept header:
```
curl -H "Accept: application/vnd.mytestapp.v3+json" http://localhost:8000/foo
```
If a specifc version header is not provided it will use the router defined by the middleware's latest version

### Handling Unsupported Versions
If a client requests a version that does not exist, the server responds with a `406 Not Acceptable` status.