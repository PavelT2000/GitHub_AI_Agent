from github.Repository import Repository

class MyRepo(Repository):
    def __init__(self, repo: Repository):
        # Копируем внутреннее состояние оригинального объекта
        self.__dict__.update(repo.__dict__)
        self._requester = repo._requester  # Важно для работы методов API внутри объекта

        # Наше новое поле
        self.downloaded: bool = False

    def __repr__(self):
        return f"<MyRepo {self.full_name} downloaded={self.downloaded}>"