from config import settings
from processing import download_repository, get_all_repositories, setup_aiignore, get_repo_information
print(__file__)
repos=get_all_repositories(settings.GITHUB_TOKEN)
download_repository(repos[1],settings.GITHUB_TOKEN)
setup_aiignore(repos[1])
# print(get_repo_information(repos[1]))

print(repos)
