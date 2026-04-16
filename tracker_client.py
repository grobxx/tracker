import config
from yandex_tracker_client.exceptions import NotFound
from tracker_connection import get_tracker_client

def get_tasks(project_key=None, limit=None):
    """Получает задачи из указанного проекта."""
    if project_key is None:
        project_key = config.DEFAULT_PROJECT_KEY
    if limit is None:
        limit = config.DEFAULT_TASKS_LIMIT

    try:
        # Инициализируем клиент (org_id или cloud_org_id из .env)
        client = get_tracker_client()

        # Проверка подключения: пробуем получить информацию о текущем пользователе
        # Если здесь ошибка, значит проблема с токеном или org_id
        current_user = client.myself
        print(f"✅ Подключение успешно. Пользователь: {current_user.display}")

        # Формируем поисковый запрос. 'Queue: {project_key}' - это стандартный синтаксис.
        query = f'Queue: {project_key}'
        print(f"🔍 Ищу задачи по запросу: '{query}'")

        # Выполняем поиск
        issues = client.issues.find(query, per_page=limit)

        tasks = []
        for issue in issues:
            tasks.append({
                "key": issue.key,
                "summary": issue.summary,
                "status": issue.status.name,
                "assignee": issue.assignee.displayName if issue.assignee else "Не назначен",
                "created_at": issue.createdAt[:10] if hasattr(issue, 'createdAt') else None,
            })

        if not tasks:
            print(f"⚠️ Задачи по запросу '{query}' не найдены.")
        else:
            print(f"✅ Найдено и обработано {len(tasks)} задач.")

        return tasks

    except NotFound:
        # Специфичная ошибка, когда очередь (проект) не найдена
        print(f"❌ Ошибка: Проект с ключом '{project_key}' не найден.")
        print("💡 Попробуйте получить список всех доступных проектов (очередей), раскомментировав код ниже.")
        # Раскомментируйте следующий блок, чтобы увидеть список доступных очередей
        # try:
        #     client = TrackerClient(token=config.TRACKER_TOKEN, org_id=config.TRACKER_ORG_ID)
        #     print("\nСписок доступных очередей (первые 5):")
        #     for q in client.queues.get_all()[:5]:
        #         print(f"  - Ключ: '{q.key}', Название: '{q.name}'")
        # except Exception as e:
        #     print(f"Не удалось получить список очередей: {e}")
        return []
    except Exception as e:
        # Обработка любых других ошибок (например, проблемы с сетью, токеном)
        print(f"❌ Непредвиденная ошибка при получении задач: {e}")
        print("Проверьте ваш OAuth-токен и ORG_ID в файле .env")
        return []