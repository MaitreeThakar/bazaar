from django.apps import AppConfig


class BazaarConfig(AppConfig):
    name = 'bazaar'

    def ready(self):
        import bazaar.signals
