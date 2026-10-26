def screen(subject, lists):
    hit = lists.match(subject)
    screening_result = ScreeningResult(subject=subject, hit=hit)
    return screening_result
