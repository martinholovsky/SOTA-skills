from enum import Flag, auto


class Perm(Flag):
    READ = auto()
    WRITE = auto()
