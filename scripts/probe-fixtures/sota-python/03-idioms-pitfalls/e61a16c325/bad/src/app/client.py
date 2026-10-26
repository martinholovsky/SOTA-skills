class Client:
    def get(self, url):
        """Deprecated: use fetch() instead."""
        return self.fetch(url)
