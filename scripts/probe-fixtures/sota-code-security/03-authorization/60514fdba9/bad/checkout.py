@app.get("/checkout/return")
def checkout_return():
    if request.args.get("status") == "paid":
        fulfil(request.args["order"])
    return redirect("/thanks")
