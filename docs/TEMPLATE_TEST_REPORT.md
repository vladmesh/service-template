# Template Test Report: BookTracker Project

**Date:** 2025-12-20  
**Template:** service-template  
**Test Goal:** Generate and test a real project using copier template

---

## Project Idea

**BookTracker** — Personal reading tracker with:
- Backend API for managing books
- Telegram bot for quick interactions (add book, mark as read)
- Notifications worker for reading reminders

---

## Step-by-Step Log

### 1. Copier Generation

**Command:** 
```bash
copier copy --trust --defaults \
  -d project_name=booktracker \
  -d modules="backend,tg_bot" \
  /workspace /output
```

**Observations:**
- ✅ Success! Copier version 9.4.1 worked without issues
- ✅ Template tasks executed correctly (removed frontend, notifications_worker)
- ✅ `.copier-answers.yml` saved correctly
- ⚠️ **Issue #1:** `services.yml` for tg_bot is missing `redis: service_healthy` in `depends_on`
  - The template hardcodes old version without redis dependency

---

## Issues Found

### Critical (Blocking)

1. **`list[]` output types not supported in domain specs**
   - Error: `Unknown output model 'list[BookRead]'`
   - Impact: Cannot define list endpoints (GET /books)
   - Workaround: Define manually or create wrapper model

2. **Generated controller has wrong indentation - methods outside class**
   ```python
   class BooksController(BooksControllerProtocol):
       """Implementation of BooksControllerProtocol."""

   async def create_book(  # ← WRONG! Should be indented inside class
       self,
       ...
   ```
   - Impact: Controller is broken, won't work at all
   - This is a code generation bug in `controllers.py` generator

### Major (Workflow Impact)

1. **File permissions after copier generation**
   - Files owned by root when generated via Docker
   - Fix required: `docker run alpine chown -R ...`
   - Adds friction for new users

2. **tg_bot missing redis dependency in services.yml template**
   - `depends_on` has `backend: service_started` but missing `redis: service_healthy`
   - Template diverged from original project

### Minor (Polish)

1. **Copier says "version None"** during copy
   - `Copying from template version None`
   - Should show git tag or branch

---

## Missing Features / Wishlist

1. **List endpoint support in specs** — need `output: list[Model]` to work
2. **Query parameters in domain specs** — for filtering/pagination  
3. **Enum types for fields** — `status` should be an enum, not string
4. **Post-generation chown** — copier should fix permissions automatically

---

## Summary

The template **works for basic cases** but has **critical bugs** that need fixing:

| What Worked | What Failed |
|-------------|-------------|
| Copier generation ✅ | Controller indentation ❌ |
| Module selection ✅ | list[] output types ❌ |
| Lint/Tests ✅ | File permissions ⚠️ |
| Schema generation ✅ | Template drift ⚠️ |
| Router generation ✅ | |

**Verdict:** Not production-ready for new projects until controller generation is fixed.
