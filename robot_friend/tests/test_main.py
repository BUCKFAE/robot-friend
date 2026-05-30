from robot_friend.main import greet


def test_greet_default():
    assert greet() == "Hello, World"


def test_greet_named():
    assert greet("Finch") == "Hello, Finch"
