from processing import get_all_repositories
from readme_generator import get_readme

# repos = get_all_repositories()
# target_repo = repos[1]

print("Генерация README.md...")
readme_md = get_readme("https://github.com/Toxa228f/TI")

print("\n--- СГЕНЕРИРОВАННЫЙ README.MD ---")
print(readme_md)