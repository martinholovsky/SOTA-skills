@app.get("/orders")
def orders():
    try:
        return jsonify(db.fetch_orders(request.args["q"]))
    except DatabaseError:
        log.exception("order query failed")
        return jsonify({"error": "request failed"}), 500
