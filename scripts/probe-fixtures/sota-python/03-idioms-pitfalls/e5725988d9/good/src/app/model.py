from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Point:
    x: int
    y: int
