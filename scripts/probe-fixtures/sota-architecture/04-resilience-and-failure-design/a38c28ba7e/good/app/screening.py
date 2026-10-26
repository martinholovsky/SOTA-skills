def screen(subject, lists):
    hit = lists.match(subject)
    screening_result = ScreeningResult(subject=subject, hit=hit, list_version=lists.version, as_of=lists.as_of)
    screenshot_result = capture(page)
    return screening_result
