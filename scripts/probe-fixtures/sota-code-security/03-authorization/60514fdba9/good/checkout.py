@app.get("/checkout/return")
def checkout_return():
    session_ref = request.args.get("session_ref")
    return redirect("/orders/pending?ref=%s" % quote(session_ref))  # fulfilment runs from the signed webhook
