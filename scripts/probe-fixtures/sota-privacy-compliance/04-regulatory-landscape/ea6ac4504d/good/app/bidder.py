def child_directed(bid_request):
    return site_policy.is_child_directed(bid_request["site"]["id"], default=True)
