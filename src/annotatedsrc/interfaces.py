from zope.interface import Interface

class IGitFetcher(Interface):
    def fetch(url, ref):
        pass
