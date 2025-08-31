# 🛡️ Настройка защиты веток

## 📋 Инструкция по защите веток main и testing

### 🔐 Ветка `main` (Продакшен)

**Настройки защиты:**
- ✅ **Require a pull request before merging**
  - Required approving reviews: **2**
  - Dismiss stale reviews: **Включено**
  - Require review from code owners: **Включено**
  
- ✅ **Require status checks to pass before merging**
  - Require branches to be up to date: **Включено**
  - Status checks:
    - `tests` (тестирование модулей)
    - `security-scan` (проверка безопасности)
    - `lint` (проверка стиля кода)

- ✅ **Require conversation resolution before merging**

- ✅ **Restrict pushes that create files larger than 100MB**

- ✅ **Require signed commits**

- ✅ **Lock branch** (только через PR)

### 🧪 Ветка `testing` (Тестирование)

**Настройки защиты:**
- ✅ **Require a pull request before merging**
  - Required approving reviews: **1**
  - Dismiss stale reviews: **Включено**
  
- ✅ **Require status checks to pass before merging**
  - Status checks:
    - `tests` (базовые тесты)
    - `build` (сборка проекта)

- ✅ **Restrict pushes that create files larger than 50MB**

- ✅ **Lock branch** (только через PR)

### 📚 Ветка `legacy` (Архив)

**Настройки защиты:**
- ✅ **Require a pull request before merging**
  - Required approving reviews: **1**
  
- ⚠️ **Allow force pushes** (только для исторических исправлений)

## 🚀 Пошаговая настройка на GitHub

### 1️⃣ Перейдите в репозиторий
https://github.com/Abilka94/WoW-Reg-Legion-Bot

### 2️⃣ Откройте Settings
Repository → Settings → Branches

### 3️⃣ Добавьте правило для ветки `main`
```
Branch name pattern: main
```

**Настройки:**
- [x] Restrict pushes that create files larger than 100 MB
- [x] Require a pull request before merging
  - [x] Required number of reviewers before merging: 2
  - [x] Dismiss stale reviews when new commits are pushed
  - [x] Require review from code owners
- [x] Require status checks to pass before merging
  - [x] Require branches to be up to date before merging
- [x] Require conversation resolution before merging
- [x] Require signed commits
- [x] Lock branch

### 4️⃣ Добавьте правило для ветки `testing`
```
Branch name pattern: testing
```

**Настройки:**
- [x] Restrict pushes that create files larger than 50 MB
- [x] Require a pull request before merging
  - [x] Required number of reviewers before merging: 1
  - [x] Dismiss stale reviews when new commits are pushed
- [x] Require status checks to pass before merging
- [x] Lock branch

### 5️⃣ Добавьте правило для ветки `legacy`
```
Branch name pattern: legacy
```

**Настройки:**
- [x] Require a pull request before merging
  - [x] Required number of reviewers before merging: 1
- [x] Allow force pushes (для исторических исправлений)

## 🔧 Альтернативный способ: GitHub CLI

Если у вас установлен GitHub CLI, можно использовать команды:

```bash
# Защита ветки main
gh api repos/Abilka94/WoW-Reg-Legion-Bot/branches/main/protection \
  --method PUT \
  --field required_status_checks='{"strict":true,"contexts":["tests","security-scan"]}' \
  --field enforce_admins=true \
  --field required_pull_request_reviews='{"required_approving_review_count":2,"dismiss_stale_reviews":true}' \
  --field restrictions=null

# Защита ветки testing
gh api repos/Abilka94/WoW-Reg-Legion-Bot/branches/testing/protection \
  --method PUT \
  --field required_status_checks='{"strict":true,"contexts":["tests","build"]}' \
  --field enforce_admins=true \
  --field required_pull_request_reviews='{"required_approving_review_count":1,"dismiss_stale_reviews":true}' \
  --field restrictions=null
```

## ⚡ Автоматизация через GitHub Actions

Создать файл `.github/workflows/branch-protection.yml` для автоматической настройки защиты веток.

## 🎯 Результат

После настройки:
- ❌ **Прямые push в main и testing запрещены**
- ✅ **Только через Pull Request**
- ✅ **Обязательное ревью кода**
- ✅ **Автоматические проверки**
- ✅ **Защита от случайных изменений**

## 🚨 Экстренный доступ

В случае критической ситуации администратор может:
1. Временно отключить защиту ветки
2. Сделать необходимые изменения
3. Снова включить защиту

**⚠️ Используйте только в крайних случаях!**