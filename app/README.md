# Вивида (приложение)

Десктопное приложение, позволяющее загружать данные пациента с глиобластомой, отправлять их в локальный ML-сервис и получать рекомендации по оптимизации протокола лечения.

---

## Принцип работы

1. **Ввод данных** — врач заполняет карточку пациента: обязательные клинические параметры и опциональные (дозировки, генетические маркеры, неврологические симптомы).
2. **ML-анализ** — приложение отправляет данные на локальный REST API. Сервис находит глобальный и локальный оптимум и формирует рекомендацию: `optimal` / `minor_change` / `major_change`.
3. **Хранение** — результаты сохраняются в локальную SQLite БД и доступны при повторном открытии карточки.

---

## Стек приложения

| Слой | Технология |
|---|---|
| Платформа | .NET 10, C# |
| UI | Avalonia UI 11.3.12 |
| Архитектура | MVVM — CommunityToolkit.Mvvm 8.2.1 |
| База данных | SQLite через EF Core 9 |
| HTTP-клиент | System.Net.Http.HttpClient |

---

## Запуск

### 1. ML-сервис (обязателен для анализа)

[Инструкция по запуску](../model/README.md#запуск)

### 2. Приложение

```bash
cd vivida
dotnet run
```

При первом запуске автоматически создаётся файл `vivida.db` рядом с исполняемым файлом. Соединение с ML API не обязательно для работы с интерфейсом — статус проверяется через меню «Сервис → Статус сервиса».

### Требования

- .NET 10 SDK
- Linux / Windows / macOS (любая платформа, поддерживаемая Avalonia)

---

## Модели данных

### `Patient` — карточка пациента

| Поле | Тип | Описание |
|---|---|---|
| `Id` | int | Первичный ключ (авто) |
| `PatientId` | string | Уникальный код вида `PAT-XXXXXXXX` (авто) |
| `Name` | string | ФИО |
| `CreatedAt` | DateTime | Дата добавления (UTC) |
| `Age` | double | Возраст, лет |
| `TumorSizeBefore` | double | Размер опухоли до лечения, см³ |
| `Kps` | double | Шкала Карновского (0–100) |
| `Treatment` | string | Тип лечения: `chemoradiotherapy` / `chemotherapy` / `radiation` |
| `DoseMgPerM2` | double? | Доза химиопрепарата, мг/м² |
| `Cycles` | int? | Количество циклов химиотерапии |
| `TotalDoseGy` | double? | Суммарная доза облучения, Гр |
| `Fractions` | int? | Количество фракций |
| `MgmtMethylation` | bool | Метилирование промотора MGMT |
| `IdhMutation` | bool | Мутация IDH |
| `EgfrAmplification` | bool | Амплификация EGFR |
| `TertMutation` | bool | Мутация TERT |
| `AtrxMutation` | bool | Мутация ATRX |
| `EdemaVolume` | double? | Объём перитуморального отёка, см³ |
| `SteroidDose` | double? | Суточная доза стероидов, мг |
| `AntiseizureMeds` | bool | Противосудорожная терапия |
| `HasHeadache` … `HasVisualDisturbance` | bool | Неврологические симптомы |
| `Gender` | string? | `male` / `female` |
| `ResectionExtent` | string? | `total` / `subtotal` / `biopsy` |
| `TumorLocation` | string? | Локализация опухоли |
| `ContrastEnhancement` | bool | Контрастное усиление |
| `Stage` | string? | Стадия |
| `Lateralization` | string? | `left` / `right` |
| `RanoResponse` | string? | Ответ по критериям RANO |
| `FamilyHistory` | bool | Семейный онкоанамнез |
| `PreviousRadiation` | bool | Предшествующее облучение |

### `AnalysisResult` — результат анализа

| Поле | Тип | Описание |
|---|---|---|
| `Id` | int | Первичный ключ |
| `PatientDbId` | int | FK → `Patient.Id` |
| `CreatedAt` | DateTime | Время анализа (UTC) |
| `ResultJson` | string | Полный JSON-ответ от API |

---

## Структура приложения

```
vivida/
├── vivida.sln
└── vivida/
    ├── Models/
    │   ├── Patient.cs          # EF Core-сущность пациента
    │   ├── AnalysisResult.cs   # EF Core-сущность результата
    │   └── ApiModels.cs        # DTO для REST API (запрос / ответ)
    ├── Data/
    │   └── AppDbContext.cs     # DbContext, настройка FK
    ├── Services/
    │   ├── DatabaseService.cs  # CRUD: пациенты и результаты
    │   ├── ApiService.cs       # HTTP-клиент: /health, /optimize/summary
    │   └── PatientService.cs   # Сборка OptimizeSummaryRequest из Patient
    ├── Converters/
    │   └── BoolToYesNoConverter.cs  # IValueConverter → «Да» / «Нет»
    ├── ViewModels/
    │   ├── MainWindowViewModel.cs   # Список пациентов, вкладки, команды меню
    │   ├── PatientTabViewModel.cs   # Карточка-вкладка: отображение, анализ
    │   └── AddPatientViewModel.cs   # Форма ввода с валидацией
    └── Views/
        ├── MainWindow.axaml(.cs)        # Главное окно: меню, список, вкладки
        ├── PatientTabView.axaml(.cs)    # UserControl: данные пациента + результат
        ├── AddPatientWindow.axaml(.cs)  # Модальное окно добавления пациента
        ├── MessageDialog.axaml(.cs)     # Информационный диалог
        └── ConfirmDialog.axaml(.cs)     # Диалог подтверждения (Да / Нет)
```

### Ключевые архитектурные решения

- **Без DI-контейнера** — сервисы создаются вручную в `App.axaml.cs` и передаются через конструкторы.
- **Compiled Avalonia bindings** — `AvaloniaUseCompiledBindingsByDefault=true`; каждый View имеет `x:DataType`.
- **Диалоги через события** — ViewModel объявляет `event Func<Task<T>>`, View подписывается в `OnOpened` и открывает окно через `ShowDialog`.
