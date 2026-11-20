import socket


def test_can_reach_example_host() -> None:
    with socket.create_connection(("example.com", 443), timeout=5):
        pass
