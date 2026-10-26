import pandas as pd


async def report(request):
    return pd.DataFrame(await load(request)).to_json()
