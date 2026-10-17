# reportkit — design notes

## Decisions

### No web framework
The spec requires a plain class whose methods take a `request` dict.
`ReportService` in `service.py` is that class.  It is framework-agnostic;
a WSGI/ASGI adapter would extract headers, body, and query params into the
dict shape and call the appropriate method.

### Request dict shape
