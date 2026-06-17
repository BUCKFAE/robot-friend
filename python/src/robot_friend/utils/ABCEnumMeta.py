from abc import ABCMeta
from enum import EnumMeta


class ABCEnumMeta(EnumMeta, ABCMeta):
    """Metaclass that lets an ``ABC`` mixin coexist with ``Enum``.

    ``ABC`` uses ``ABCMeta`` and ``Enum`` uses ``EnumMeta``; combining them in a
    single class otherwise raises a metaclass conflict.

    """
