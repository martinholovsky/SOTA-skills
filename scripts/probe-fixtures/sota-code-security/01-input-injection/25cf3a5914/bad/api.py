@app.get("/orders")
def orders():
    try:
        return jsonify(db.fetch_orders(request.args["q"]))
    except DatabaseError as e:
        return jsonify({"error": str(e)}), 500
