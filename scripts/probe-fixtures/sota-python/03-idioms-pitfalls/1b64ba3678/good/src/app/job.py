def run():
    try:
        step()
    except TimeoutError:
        retry()
