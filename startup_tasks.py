class StartupTask:
    bot = None
    tasks = []

    def __init__(self, async_func):
        self.tasks.append(async_func())

    @staticmethod
    def set_bot(bot):
        StartupTask.bot = bot
