import asyncio


class AsyncLoopManager:
    """Classe singleton pour gérer une boucle d'événements asynchrone partagée dans les tâches Celery"""
    _loop = None


    def get_loop(self):
        """Retourne la boucle d'événements asynchrone partagée"""
        if self._loop is None:
            self._loop = asyncio.get_event_loop()
            asyncio.set_event_loop(self._loop)
        return self._loop

    def run_async(self, couroutine):
        """Exécute une coroutine dans la boucle d'événements partagée"""
        loop = self.get_loop()
        return loop.run_until_complete(couroutine)

task_async_loop_manager = AsyncLoopManager()