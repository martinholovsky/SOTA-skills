def call_crm(request, query):
    token = exchange_token(subject=request.user, audience="crm", scope="crm.read")
    return httpx.get(CRM_URL, params={"q": query}, headers={"Authorization": f"Bearer {token}"})
