from azure.rag import request_context


def test_emit_token_is_a_noop_without_a_sink():
    request_context.emit_token("merhaba")  # yükseltmemeli


def test_emit_token_reaches_the_installed_sink():
    received: list[str] = []
    token = request_context.set_token_sink(received.append)
    try:
        request_context.emit_token("mer")
        request_context.emit_token("haba")
    finally:
        request_context.reset_token_sink(token)

    assert received == ["mer", "haba"]


def test_sink_is_removed_after_reset():
    received: list[str] = []
    token = request_context.set_token_sink(received.append)
    request_context.reset_token_sink(token)

    request_context.emit_token("gitmemeli")

    assert received == []


def test_upload_store_round_trips_through_the_context():
    sentinel = object()
    token = request_context.set_upload_store(sentinel)
    try:
        assert request_context.active_upload_store() is sentinel
    finally:
        request_context.reset_upload_store(token)

    assert request_context.active_upload_store() is None
