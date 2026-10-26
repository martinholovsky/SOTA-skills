def call_crm(request, query):
    return httpx.get(CRM_URL, params={"q": query},
                     headers={"Authorization": request.headers["Authorization"]})
