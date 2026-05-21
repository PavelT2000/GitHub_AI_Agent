from config import settings
from processing import download_repository, get_all_repositories, setup_aiignore, get_repo_information, generate_readme

# 1. Получаем список и скачиваем репозиторий
repos = get_all_repositories()
target_repo = repos[1]  # Работаем с выбранным репозиторием
download_repository(target_repo)

# 2. Настраиваем игнорирование (если нужно обновить правила)
# setup_aiignore(target_repo)

# 3. Собираем умный контекст проекта (например, в рамках лимита 40 000 токенов)
print("Сборка контекста проекта...")
context = get_repo_information(target_repo, token_limit=20000)

# 4. Передаем этот контекст ИИ для написания README.md
print("Генерация README.md...")
readme_md = generate_readme(target_repo, context)

# Выводим результат в консоль
print("\n--- СГЕНЕРИРОВАННЫЙ README.MD ---")
print(readme_md)