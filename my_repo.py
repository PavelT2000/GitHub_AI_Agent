from github.Repository import Repository

class MyRepo(Repository):
    def __init__(self, repo: Repository):
        self.__dict__.update(repo.__dict__)
        self._requester = repo._requester
        self.downloaded: bool = False

    def __repr__(self):
        return f"<MyRepo {self.full_name} downloaded={self.downloaded}>"