# Security Policy

## Supported Versions

We actively maintain security updates for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

---

## Reporting a Vulnerability

We take the security of **ResumeForge AI** seriously. If you believe you have found a security vulnerability, please do **NOT** report it in a public GitHub issue.

Instead, please report security vulnerabilities privately:
1. Contact the maintainer privately via GitHub profile contact or email: `mahenderkheechar@gmail.com`.
2. Provide detailed steps to reproduce the vulnerability, including:
   * Description of the issue
   * Proof-of-concept exploit code or reproduction steps
   * Impact assessment
3. You will receive an acknowledgment within 48 hours.

---

## Security Best Practices for Self-Hosting

* **Never commit `.env` files**: Ensure API keys and database credentials remain secret.
* **Keep dependencies updated**: Periodically run `npm audit` and `pip audit` or update your requirements.
* **Use HTTPS & TLS in Production**: Always configure SSL/TLS certificates when deploying backend and frontend services.
