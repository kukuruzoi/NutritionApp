# Nutrition Tracker — Трекер питания

Десктопное приложение для учёта рациона, контроля КБЖУ и отслеживания прогресса веса.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14+-blue.svg)
![Tkinter](https://img.shields.io/badge/GUI-Tkinter-orange.svg)

## Оглавление
- [Возможности](#-возможности)
- [Установка](#-установка)
- [Использование](#-использование)
- [Скриншоты](#-cкриншоты)
- [Технологии](#-технологии)

## Возможности

- **Безопасная авторизация** с хешированием паролей (bcrypt)
- **Дневник питания** с календарём и переключением дат
- **Справочник продуктов** с поиском и категориями
- **Автоматический расчёт** КБЖУ для порций
- **Прогресс веса** с визуализацией (Progress Bar)
- **Готовые планы питания** (7-дневные циклы)
- **Кастомные аватары**
- **Авто-сохранение** сессии

## Установка

### 1. Требования
- Python 3.10 или выше
- PostgreSQL 14 или выше

### 2. Клонирование репозитория
```bash
git clone https://github.com/kukuruzoi/NutritionApp.git
cd NutritionApp
```

### 3. Установка зависимостей
```bash
pip install -r requirements.txt
```

### 4. Настройка базы данных
Создайте базу данных и выполните скрипты инициализации:
```bash
createdb nutrition_tracker

psql -d nutrition_tracker -f database/init.sql
```

### 5. Конфигруация
1. Скопируйте пример конфигурации:
 ```bash
cp config.example.py config.py
```
2. Отредактируйте config.py, указав ваши данные для подключения к PostgreSQL:
```bash
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'nutrition_tracker',
    'user': 'ваш_пользователь',
    'password': 'ваш_пароль'
}
```

## Использование

### Запуск приложения
 ```bash
python main.py
```

### Первый вход

- Нажмите "Я новый пользователь"
- Введите логин (3–255 символов) и пароль
- Заполните профиль (рост, вес, цель)
- Начните добавлять продукты либо подключите готовый  план

### Основные функции

- Добавить продукт: Выберите приём пищи → Кнопка "Добавить продукт" → Поиск → Укажите вес еды
- Применить план: Подключите план в разделе "Планы питания" → Нажмите "Применить план"
- Отследить вес: Профиль → "Обновить вес" → Введите текущий вес

## Скриншоты

### Экран авторизации

![экран_авторизации](https://github.com/kukuruzoi/NutritionApp/blob/main/img/screenshots/auth_frame.png?raw=true)

### Главный экран

![главный_экран](https://github.com/kukuruzoi/NutritionApp/blob/main/img/screenshots/main_frame.png?raw=true)

### Прогресс веса

![прогресс_веса](https://github.com/kukuruzoi/NutritionApp/blob/main/img/screenshots/progress_weight.png?raw=true)

## Технологии

- Язык: Python 3.10+
- GUI: Tkinter
- СУБД: PostgreSQL 14+
- Библиотеки:
  - psycopg2 — драйвер PostgreSQL
  - bcrypt — хеширование паролей
  - Pillow — обработка изображений
