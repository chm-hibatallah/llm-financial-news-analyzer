# Documentation Index

Complete reference documentation for FinSentiment Lab.

## Main Documentation

- **[README.md](../README.md)** - Main project overview (START HERE)

## Secondary Documentation

### Setup & Operations

- **[STREAMING.md](STREAMING.md)** - Real-time price streaming setup and configuration
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System architecture and data flow

### Development & Technical

- **[MIGRATION.md](MIGRATION.md)** - Project structure migration summary
- **[IMPORTS.md](IMPORTS.md)** - Complete Python import analysis and dependency tree
- **[CHECKLIST.md](CHECKLIST.md)** - Migration checklist and verification steps

---

## Quick Navigation

### Getting Started
1. Read [../README.md](../README.md) for overview
2. Follow "Quick Start" section to install
3. Run `python main.py &` and `streamlit run .streamlit/streamlit_app.py`

### Running Real-Time Features
1. Check [STREAMING.md](STREAMING.md) for streaming setup
2. Run `python stream_prices.py` in separate terminal
3. Watch live prices on dashboard

### Understanding the System
1. See [ARCHITECTURE.md](ARCHITECTURE.md) for system design
2. Review [IMPORTS.md](IMPORTS.md) for module dependencies
3. Check [MIGRATION.md](MIGRATION.md) for structural changes

### Development & Extension
1. Review [CHECKLIST.md](CHECKLIST.md) for verified modules
2. Check import patterns in [IMPORTS.md](IMPORTS.md)
3. Follow existing module structure when adding new features

---

## File Organization

```
docs/
├── INDEX.md              (This file)
├── STREAMING.md          (Price streaming setup)
├── ARCHITECTURE.md       (System design)
├── MIGRATION.md          (Structure changes)
├── IMPORTS.md            (Module analysis)
└── CHECKLIST.md          (Verification steps)
```

---

## Document Descriptions

| Document | Purpose | Audience |
|----------|---------|----------|
| STREAMING.md | Setup real-time price feeds | Operators, Users |
| ARCHITECTURE.md | Understand system design | Developers, Architects |
| MIGRATION.md | Historical record of changes | Maintainers |
| IMPORTS.md | Module dependency reference | Developers |
| CHECKLIST.md | Verify system integrity | DevOps, QA |

---

Last Updated: April 7, 2026
