# FinanceAnalyzer

FinanceAnalyzer/
├── frontEnd/
│   ├── public/                    # Публичные статические файлы
│   │   ├── index.html
│   │   ├── favicon.ico
│   │   ├── robots.txt
│   │   └── assets/                # Изображения и другие ресурсы
│   ├── src/
│   │   ├── index.jsx              # Точка входа
│   │   ├── App.jsx                # Основной компонент приложения
│   │   ├── constants.js           # Константы приложения
│   │   ├── api/                   # API клиент
│   │   │   ├── index.js           # Конфигурация Axios
│   │   │   ├── auth.js            # API для аутентификации
│   │   │   ├── user.js            # API для пользователей
│   │   │   ├── upload.js          # API для загрузки файлов
│   │   │   └── analysis.js        # API для анализа
│   │   ├── assets/                # Статические ресурсы
│   │   │   ├── css/               # CSS стили
│   │   │   ├── images/            # Изображения
│   │   │   └── fonts/             # Шрифты
│   │   ├── components/            # UI компоненты
│   │   │   ├── common/            # Общие компоненты
│   │   │   │   ├── Button.jsx
│   │   │   │   ├── Input.jsx
│   │   │   │   ├── Loader.jsx
│   │   │   │   └── Modal.jsx
│   │   │   ├── layout/            # Компоненты макета
│   │   │   │   ├── Header.jsx
│   │   │   │   ├── Footer.jsx
│   │   │   │   ├── Sidebar.jsx
│   │   │   │   └── Layout.jsx
│   │   │   ├── auth/              # Компоненты аутентификации
│   │   │   │   ├── LoginForm.jsx
│   │   │   │   └── RegisterForm.jsx
│   │   │   ├── upload/            # Компоненты загрузки
│   │   │   │   ├── FileUpload.jsx
│   │   │   │   └── UploadProgress.jsx
│   │   │   ├── dashboard/         # Компоненты дашборда
│   │   │   │   ├── Summary.jsx
│   │   │   │   ├── RecentUploads.jsx
│   │   │   │   └── Statistics.jsx
│   │   │   ├── analysis/          # Компоненты анализа
│   │   │   │   ├── IncomeChart.jsx
│   │   │   │   ├── ExpenseChart.jsx
│   │   │   │   ├── TransactionList.jsx
│   │   │   │   └── TaxCalculation.jsx
│   │   │   └── admin/             # Компоненты администрирования
│   │   │       ├── UserList.jsx
│   │   │       ├── BankList.jsx
│   │   │       └── EventLog.jsx
│   │   ├── contexts/              # React контексты
│   │   │   ├── AuthContext.jsx
│   │   │   └── ThemeContext.jsx
│   │   ├── hooks/                 # Пользовательские хуки
│   │   │   ├── useAuth.js
│   │   │   ├── useFileUpload.js
│   │   │   └── useAnalysis.js
│   │   ├── pages/                 # Страницы приложения
│   │   │   ├── HomePage.jsx
│   │   │   ├── LoginPage.jsx
│   │   │   ├── RegisterPage.jsx
│   │   │   ├── DashboardPage.jsx
│   │   │   ├── AnalysisResultPage.jsx
│   │   │   ├── ProfilePage.jsx
│   │   │   └── AdminPage.jsx
│   │   ├── services/              # Сервисы
│   │   │   ├── auth.service.js
│   │   │   ├── user.service.js
│   │   │   ├── file.service.js
│   │   │   └── analysis.service.js
│   │   └── utils/                 # Утилиты
│   │       ├── formatters.js      # Форматирование данных
│   │       ├── validators.js      # Валидация форм
│   │       └── helpers.js         # Вспомогательные функции
│   ├── .env                       # Переменные окружения
│   ├── .gitignore                 # Файлы, игнорируемые Git
│   ├── package.json               # Зависимости NPM
│   ├── README.md                  # Документация
│   ├── .eslintrc.js               # Настройки ESLint
│   └── vite.config.js             # Конфигурация Vite