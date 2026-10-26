async def report(request):
    import pandas as pd
    return pd.DataFrame(await load(request)).to_json()
