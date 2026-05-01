from config import settings
from github_exec import download_repository, get_all_repositories, setup_aiignore
from github_exec import get_filtered_hierarchy

repos=get_all_repositories(settings.GITHUB_TOKEN)
download_repository(repos[1],settings.GITHUB_TOKEN)
setup_aiignore(repos[1]) 
print(get_filtered_hierarchy(repos[1]))

print(repos)
