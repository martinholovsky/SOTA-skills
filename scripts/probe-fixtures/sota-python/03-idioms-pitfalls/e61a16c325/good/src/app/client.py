from warnings import deprecated


class Client:
    @deprecated("Use fetch() instead; removed in 3.0")
    def get(self, url):
        return self.fetch(url)
