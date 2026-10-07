class MockError(Exception):
    """Base for errors raised by the mock framework itself, as opposed to errors a mock is told to raise."""


class MockConfigError(MockError):
    """A mock's declared behaviour cannot be used: an unknown method or error, or an invalid outcome."""


class UnmockedCallError(MockError):
    """A strict mock was called on a method it declares no behaviour for."""
