def report(line_num: int | None) -> None:
    if line_num is not None:
        emit(line_num)
