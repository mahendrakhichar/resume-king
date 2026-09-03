# Contributing to ResumeForge AI

Thank you for your interest in contributing to **ResumeForge AI**! We welcome contributions of all kinds: bug fixes, new features, documentation improvements, UI enhancements, and community feedback.

---

## 📜 Code of Conduct

By participating in this project, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md). Please treat all contributors with respect.

---

## 🛠️ Getting Started

1. **Fork the repository** on GitHub.
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/<your-username>/resume-king.git
   cd resume-king
   ```
3. **Add the upstream remote**:
   ```bash
   git remote add upstream https://github.com/mahendrakhichar/resume-king.git
   ```

---

## 🌿 Branching Strategy

* Always branch off `main`.
* Use descriptive branch names:
  * `feature/issue-short-description` (for new features)
  * `fix/issue-short-description` (for bug fixes)
  * `docs/update-readme` (for documentation updates)

```bash
git checkout -b feature/awesome-new-agent
```

---

## 💻 Development Workflow

### Backend Development
* Follow PEP 8 style conventions.
* Type annotations are encouraged for all function parameters and return types.
* Keep agent prompt engineering modular inside `backend/agents/` and `backend/prompts/`.
* Test endpoints locally using FastAPI's automatic Swagger docs at `http://localhost:8000/docs`.

### Frontend Development
* Use React function components and TypeScript.
* Follow Tailwind CSS patterns already in place in `frontend/src/index.css`.
* Ensure linting and TypeScript checks pass:
  ```bash
  cd frontend
  npm run build
  ```

---

## 📬 Submitting a Pull Request (PR)

1. Ensure your local branch is rebased onto the latest `upstream/main`:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```
2. Commit your changes using semantic commit messages:
   * `feat: ...` for new features
   * `fix: ...` for bug fixes
   * `docs: ...` for documentation changes
   * `refactor: ...` for code refactoring
3. Push to your fork:
   ```bash
   git push origin feature/awesome-new-agent
   ```
4. Open a Pull Request on GitHub targeting `main`. Fill in the PR template with relevant context and testing details.

---

## 🐛 Reporting Bugs & Requesting Features

* **Bug Reports**: Please open an issue using the [Bug Report template](.github/ISSUE_TEMPLATE/bug_report.md). Include reproduction steps and environment details.
* **Feature Requests**: Please open an issue using the [Feature Request template](.github/ISSUE_TEMPLATE/feature_request.md) explaining the use case and desired outcome.

Thank you for helping make ResumeForge AI better! 🚀
