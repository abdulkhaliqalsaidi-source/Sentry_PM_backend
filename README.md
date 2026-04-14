# Sentry PM — Project Management & Error Tracking Platform

<div align="center">

![Version](https://img.shields.io/badge/version-1.0.0-6366f1)
![Django](https://img.shields.io/badge/Django-5.0-092E20?logo=django)
![Vue](https://img.shields.io/badge/Vue.js-3.x-4FC08D?logo=vuedotjs)
![License](https://img.shields.io/badge/license-Envato-orange)

**A full-stack platform combining Jira-like project management with Sentry-like error tracking — fully bilingual (Arabic 🇸🇦 & English 🇬🇧), real-time WebSockets, and a stunning dark UI.**

[📖 Documentation](documentation/index.html) · [✨ Features](#features) · [🚀 Installation](#installation)

</div>

---

## 🎯 Overview

**Sentry PM** is a complete business management platform built with **Django 5** + **Vue.js 3**. It covers everything a software team needs:

- 🐛 **Error Tracking** — Capture JS exceptions, network failures, session replays
- 📋 **Project Management** — Kanban board, sprints, backlog, epics
- 📊 **Agile Reports** — Burndown/burnup charts, velocity, workload
- 💬 **Team Chat** — Real-time WebSocket chat per project
- 📝 **Documentation** — Markdown wiki with revision history & PDF export
- ⭐ **Developer Evaluations** — Quarterly scoring with leaderboard
- 🌍 **Bilingual** — Full Arabic (RTL) + English (LTR) support

---

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| 🔍 **Error Tracking** | Real-time JS error capture with stack traces |
| 📽️ **Session Replay** | Reproduce user sessions to debug issues |
| 📋 **Kanban Board** | Drag-and-drop task management |
| 🏃 **Agile Sprints** | Sprint planning with burndown charts |
| 💬 **Live Chat** | WebSocket team chat with file uploads |
| 📝 **Wiki Docs** | Markdown documentation with version history |
| ⭐ **Evaluations** | Developer performance scoring & leaderboard |
| 🔑 **Permissions** | Fine-grained role & permission groups |
| 🌙 **Dark Mode** | Premium Vibrant-Glass design system |
| 🌍 **Arabic RTL** | Full right-to-left layout support |
| 🔐 **JWT Auth** | Secure token authentication with refresh |
| 🗄️ **SQLite / PG** | SQLite (zero-config) or PostgreSQL |

---

## 🚀 Installation

### One-Command Setup

```bash
python install.py
```

### Manual Setup

```bash
# 1. Install Python dependencies
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env   # Edit with your settings

# 3. Run migrations
python manage.py migrate

# 4. Load demo data
python demo_data.py

# 5. Start backend
python manage.py runserver 3535

# 6. Start frontend (new terminal)
cd frontend && npm install && npm run dev
```

---

## 🎭 Demo Accounts

| Username | Password | Role |
|----------|----------|------|
| `admin` | `admin123` | Super Admin |
| `devuser` | `dev12345` | Developer |
| `sarah` | `sara12345` | Developer |
| `omar` | `omar12345` | Developer |

---

## ⚙️ Requirements

- **Python** 3.10+
- **Node.js** 16+
- **Database** SQLite (built-in) or PostgreSQL 14+

---

## 📁 Project Structure

```
sentry-pm/
├── config/                 # Django settings & URL config
├── tracker/                # Error tracking app
│   ├── models.py           # Error, Session, NetworkFailure models
│   ├── views.py            # REST API endpoints
│   └── serializers.py
├── project_management/     # PM app
│   ├── models.py           # Project, Task, Sprint, Epic, etc.
│   ├── views.py            # REST API endpoints
│   └── consumers.py        # WebSocket consumers
├── frontend/               # Vue.js 3 frontend
│   └── src/
│       ├── components/     # Vue components (50+)
│       ├── router/         # Vue Router config
│       └── locales/        # i18n translations (AR + EN)
├── documentation/          # HTML documentation
├── client_sdk.js           # JavaScript client SDK
├── install.py              # Automated installer
├── demo_data.py            # Demo data seeder
├── reset_demo.py           # Demo reset utility
├── requirements.txt        # Python dependencies
└── .env.example            # Environment template
```

---

## 📖 Full Documentation

Open `documentation/index.html` in your browser for the complete documentation including:
- Detailed installation steps (Windows, Linux, macOS)
- All environment variables explained
- Feature descriptions with screenshots
- FAQ (10 common questions)
- Changelog

---

## 📄 License

Licensed under the Envato Regular License. One purchase = one end product.
For SaaS / multi-use, purchase the Extended License.

© 2026 — All Rights Reserved.
