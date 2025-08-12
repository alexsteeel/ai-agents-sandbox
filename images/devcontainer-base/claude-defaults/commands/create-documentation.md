---
name: create-documentation
description: Creates user documentation in Russian by analyzing recent changes using the technical-writer agent
arguments: []
---

You are working with the Technical Writer agent to create user-friendly documentation in Russian based on recent changes in the project. The documentation should be clear, comprehensive, and accessible to non-technical users.

## Your Mission

Analyze recent changes in the project and create user documentation in Russian that explains the new features, changes, and how to use them without technical jargon.

## Step 1: Analyze Recent Changes

### 1.1 Check Git History
Examine recent commits and changes:
```bash
# Get recent commits
git log --oneline -20

# See what files changed
git diff --stat HEAD~10..HEAD

# Look at specific changes
git show --stat HEAD
```

### 1.2 Identify User-Facing Changes
Focus on changes that affect users:
- New features or functionality
- UI/UX improvements
- API changes that affect integration
- Configuration changes
- Bug fixes that users might have encountered
- Performance improvements
- Security enhancements

### 1.3 Read Implementation Files
Review the actual implementation to understand:
- What the feature does
- How users interact with it
- What problems it solves
- Any limitations or prerequisites

## Step 2: Extract Task Information

### 2.1 Determine Task Name
Look for task context from:
- Recent commit messages
- Requirements documents in tasks/ folder
- Implementation reports
- PR descriptions

### 2.2 Gather Technical Details
Understand the technical implementation to translate it for users:
- Core functionality
- Input/output expectations
- Error handling
- Performance characteristics

## Step 3: Create User Documentation in Russian

### 3.1 Documentation Structure

Create a file `tasks/<task_name>_docs.md` with the following structure:

```markdown
# [Название функции/изменения]

## Обзор
[Краткое описание того, что было добавлено или изменено, понятное обычному пользователю]

## Что нового?
- [Перечислите новые возможности простым языком]
- [Объясните преимущества для пользователя]
- [Укажите решённые проблемы]

## Как использовать

### Начало работы
[Пошаговая инструкция для начала использования]

1. **Шаг 1**: [Описание первого действия]
   - [Подробности, если необходимо]
   - [Что пользователь должен увидеть]

2. **Шаг 2**: [Следующее действие]
   - [Детали]
   - [Ожидаемый результат]

3. **Шаг 3**: [И так далее...]

### Примеры использования

#### Пример 1: [Типичный сценарий]
[Опишите конкретный пример использования с пояснениями]

```
[Если есть команды или код, покажите их]
```

**Результат**: [Что получит пользователь]

#### Пример 2: [Другой сценарий]
[Ещё один практический пример]

### Настройки и параметры

| Параметр | Описание | Значение по умолчанию | Обязательный |
|----------|----------|----------------------|--------------|
| [название] | [что делает] | [значение] | Да/Нет |

## Часто задаваемые вопросы

**В: [Типичный вопрос пользователя]**
О: [Понятный ответ без технических терминов]

**В: [Другой вопрос]**
О: [Ответ]

## Решение проблем

### Проблема: [Описание проблемы]
**Симптомы**: [Что видит пользователь]
**Решение**: [Пошаговое решение]

### Проблема: [Другая проблема]
**Симптомы**: [Признаки]
**Решение**: [Как исправить]

## Важные замечания

⚠️ **Внимание**: [Важные предупреждения или ограничения]

✅ **Совет**: [Полезные рекомендации]

ℹ️ **Примечание**: [Дополнительная информация]

## Совместимость

- **Поддерживаемые версии**: [Версии системы/браузера/и т.д.]
- **Требования**: [Что нужно для работы]
- **Ограничения**: [Известные ограничения]

## Что изменилось для существующих пользователей

Если вы уже использовали предыдущую версию:
- [Что нужно сделать для перехода]
- [Изменения в поведении]
- [Устаревшие функции]

## Безопасность

[Если есть аспекты безопасности, объясните их простым языком]
- Как защищены ваши данные
- Что нужно знать о конфиденциальности
- Рекомендации по безопасному использованию

## Производительность

[Если есть улучшения производительности]
- На сколько быстрее стало работать
- Что было оптимизировано
- Как это влияет на пользовательский опыт

## Дополнительные ресурсы

- 📖 [Ссылка на подробную документацию]
- 💬 [Где получить поддержку]
- 🐛 [Как сообщить о проблеме]

## История изменений

### Версия [X.Y.Z] - [Дата]
- ✨ Новое: [Что добавлено]
- 🐛 Исправлено: [Какие ошибки устранены]
- ⚡ Улучшено: [Что оптимизировано]
```

### 3.2 Writing Style Guidelines for Russian Documentation

**Тон и стиль**:
- Используйте простой, понятный язык
- Избегайте технического жаргона
- Обращайтесь к пользователю на "вы"
- Используйте активный залог
- Будьте дружелюбны и профессиональны

**Структура**:
- Короткие абзацы (2-3 предложения)
- Нумерованные списки для последовательных действий
- Маркированные списки для перечислений
- Таблицы для справочной информации
- Выделение важной информации

**Примеры**:
- Всегда включайте практические примеры
- Показывайте "до" и "после"
- Используйте реальные сценарии использования

### 3.3 Technical Terms Translation

When translating technical terms to Russian:
- API → API (или "программный интерфейс")
- Database → База данных
- Cache → Кеш
- Performance → Производительность
- Security → Безопасность
- Authentication → Аутентификация
- Authorization → Авторизация
- Configuration → Настройка/Конфигурация
- Dashboard → Панель управления
- Settings → Настройки
- Feature → Функция/Возможность
- Bug → Ошибка
- Update → Обновление
- Deploy → Развертывание
- Server → Сервер
- Client → Клиент

## Step 4: Include Visual Elements

Where helpful, include:
- Screenshots with annotations in Russian
- Diagrams showing workflow
- Icons for better visual navigation
- Color coding for different types of information

```markdown
💡 Подсказка: [Полезный совет]
⚠️ Предупреждение: [Важное замечание]
✅ Успех: [Положительный результат]
❌ Ошибка: [Что пошло не так]
📝 Примечание: [Дополнительная информация]
```

## Step 5: Validate Documentation

Before finalizing:
1. Check that all features are documented
2. Verify examples work correctly
3. Ensure no technical jargon remains
4. Confirm Russian grammar and spelling
5. Test instructions step-by-step

## Step 6: Create Documentation Summary

After creating the documentation, provide a summary:

```markdown
# Отчёт о создании документации

## Созданные документы
- Файл: tasks/<task_name>_docs.md
- Язык: Русский
- Целевая аудитория: Конечные пользователи (не технические специалисты)

## Задокументированные изменения
- [Список основных изменений]
- [Новые функции]
- [Исправленные проблемы]

## Ключевые разделы
- Обзор и преимущества
- Пошаговые инструкции
- Примеры использования
- Решение проблем
- Часто задаваемые вопросы

## Рекомендации
- [Что ещё можно улучшить]
- [Дополнительные материалы, которые могут понадобиться]
```

## Important Notes

- **Language**: All user documentation MUST be in Russian
- **Audience**: Non-technical users who need clear, simple explanations
- **No Technical Jargon**: Avoid or explain all technical terms
- **Practical Focus**: Emphasize what users can do, not how it works
- **Visual Aids**: Use emojis, tables, and formatting for clarity
- **Complete Coverage**: Document all user-facing changes
- **Save Location**: Store in `tasks/<task_name>_docs.md`

Begin analyzing recent changes and creating user documentation in Russian now.