import asyncio

from discordwidget.widget import Widget


def test_sync_request_uses_timeout(monkeypatch):
    widget = Widget(123, timeout=3.5)

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {}

    captured = {}

    def fake_get(url, timeout):
        captured["url"] = url
        captured["timeout"] = timeout
        return Response()

    monkeypatch.setattr("discordwidget.widget.requests.get", fake_get)

    widget._sync_request_json()

    assert captured["url"] == "https://discord.com/api/guilds/123/widget.json"
    assert captured["timeout"] == 3.5


def test_async_request_uses_timeout():
    widget = Widget(123, timeout=2.0)
    captured = {}

    class ResponseContext:
        async def __aenter__(self):
            class Response:
                status = 200

                async def json(self):
                    return {}

            return Response()

        async def __aexit__(self, exc_type, exc, tb):
            return None

    class Session:
        def get(self, url, timeout):
            captured["url"] = url
            captured["timeout"] = timeout
            return ResponseContext()

    asyncio.run(widget._async_request_json(Session()))

    assert captured["url"] == "https://discord.com/api/guilds/123/widget.json"
    assert captured["timeout"].total == 2.0
