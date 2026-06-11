# Security

**Last Updated: March 2026**

> **Beta Notice:** LeastAction is currently in Beta. Our security posture is evolving as the product matures. We are transparent about what we do and do not provide at this stage.

---

## Overview

LeastAction is **self-hosted software**. You deploy and operate it on your own infrastructure — your servers, your cloud account, your network. This has important implications for security:

**Security of your deployment — including infrastructure hardening, network configuration, TLS certificates, database access controls, backups, monitoring, and incident response — is your responsibility.** LeastAction Labs does not have access to your deployment or any data within it.

This page describes three distinct topics:

1. **Security features built into the LeastAction software** — what the application itself does to protect your data
2. **LeastAction Labs' own security practices** — how we secure the software distribution and the leastactionlabs.com marketplace website
3. **How to report a vulnerability** — our responsible disclosure process

---

## Security Features Built Into the Software

### Authentication

- **Username and password authentication:** User passwords are stored using **bcrypt** hashing with an appropriate work factor. Plaintext passwords are never stored or logged.
- **SSO / SAML 2.0:** Single Sign-On via SAML 2.0 is coming soon in the **Enterprise Edition**, enabling integration with your organization's identity provider (e.g., Okta, Azure AD, Google Workspace).
- **Session management:** Application sessions are managed via server-side session tokens. Session cookies are marked `HttpOnly` and `SameSite=Strict` to mitigate XSS and CSRF risks.

### Authorization

- **Role-Based Access Control (RBAC):** Available in the **Enterprise Edition**. Administrators can assign roles to users, restricting which workflows, operators, and administrative functions each user can access.
- **API authentication:** All API endpoints require valid authentication. Unauthenticated requests are rejected.

### Secrets Management

Connection credentials (database passwords, API keys, third-party service tokens) configured within LeastAction are stored **encrypted at rest** in the LeastAction database using **AES-256** encryption. Encryption keys are derived from a master secret configured at deployment time. The security of your master secret is your responsibility — store it securely using your infrastructure's secrets management tooling (e.g., HashiCorp Vault, AWS Secrets Manager, environment variable injection).

### Audit Trail

- **Workflow execution logs:** All workflow runs generate detailed execution logs including timestamps, operator outputs, and error states.
- **User action logs:** Administrative and user actions (login events, configuration changes, permission changes) are logged in the **Enterprise Edition**.

### Network

The LeastAction application communicates over HTTP or HTTPS depending on your deployment configuration. **TLS termination is the deployer's responsibility.** We strongly recommend placing LeastAction behind a TLS-terminating reverse proxy. See Deployment Security Guidance below.

### License Key Validation

Enterprise Edition license keys are **cryptographically signed**. The LeastAction application validates the signature at startup and periodically during operation. Tampering with license key validation logic constitutes a material breach of the [Enterprise Edition License](/license-ee).

---

## Deployment Security Guidance (Customer Responsibility)

The following guidance reflects security best practices for self-hosted deployments. This is not an exhaustive security standard — it is a starting point.

- **Use TLS.** Run LeastAction behind a TLS-terminating reverse proxy such as nginx, Caddy, or Traefik. Do not expose the application on plain HTTP in production environments.
- **Restrict network access.** Expose only the ports necessary for LeastAction to operate (typically the application HTTP port). Do not expose your database port directly to the internet.
- **Use a dedicated database user.** Create a database user with the minimum privileges required by LeastAction. Do not connect LeastAction to your database as a superuser or root user.
- **Enable OS-level firewalling.** Use your operating system's firewall (iptables, ufw, security groups) to restrict inbound and outbound traffic.
- **Keep your installation updated.** We publish security fixes and patches as part of regular releases. Subscribe to release notifications on our repository and apply updates promptly.
- **Back up your database regularly.** LeastAction's state (workflows, connections, execution history) is stored in your database. Back it up frequently and test restoration.
- **Apply the principle of least privilege** to LeastAction user accounts. Limit the number of administrator-role users. Revoke access promptly when users leave your organization.
- **Protect your master secret.** The master secret used to derive encryption keys for stored credentials must be kept secure. Rotate it according to your organization's key management policies.
- **Monitor application logs.** Review LeastAction logs for unexpected errors, authentication failures, and unusual activity.

---

## LeastAction Labs Security Practices

The following describes our own security practices for the software we distribute and for the leastactionlabs.com website.

### Software Distribution

- Software releases are published via our source repository with **signed release artifacts**. Verify release signatures before deploying in sensitive environments.
- We conduct **internal code review** for all changes before merging to the release branch.
- **Automated dependency scanning** is used to monitor our software dependencies for known CVEs (Common Vulnerabilities and Exposures). We aim to address high and critical CVEs in our dependencies promptly.

### Website and Marketplace (leastactionlabs.com)

- The leastactionlabs.com website is served exclusively over **HTTPS with HSTS** (HTTP Strict Transport Security) enabled.
- We apply standard web application security controls including CSRF protection, input validation, and output encoding.
- Administrative access to our systems requires multi-factor authentication.

### Data Access

- **LeastAction Labs has no access to data in your self-hosted deployment.** We cannot read your workflows, execution history, connection credentials, or any other data stored in your LeastAction database.
- Access to our own internal systems and the marketplace portal database is restricted to authorized personnel on a need-to-know basis.

### What We Do Not Claim

We are a small team in Beta. We are honest about our current capabilities:

- We do **not** hold SOC 2, ISO 27001, HIPAA, or other third-party compliance certifications at this time.
- We do **not** operate a 24/7 Security Operations Centre (SOC).
- We do **not** conduct formal third-party penetration tests on a regular schedule at this stage, though we plan to as the product matures.

---

## Compliance

### Customer Responsibility as Data Controller

**Self-hosted customers are the data controllers** for any personal data processed by their LeastAction deployment. LeastAction Labs is not a data processor for self-hosted deployments. We have no contractual or legal access to your deployment data.

Customers who require GDPR, HIPAA, SOC 2, PCI-DSS, or other compliance standards for their deployment must perform their own compliance assessment of their deployment environment. LeastAction Labs can provide **architecture documentation** to support such assessments — contact us at [security@leastactionlabs.com](mailto:security@leastactionlabs.com).

### BC Public Sector Clients

If you are a British Columbia public sector organization subject to **FOIPPA (Freedom of Information and Protection of Privacy Act)**, the data residency and storage requirements of FOIPPA apply to your LeastAction deployment. LeastAction can be deployed on Canadian-hosted infrastructure (including Canadian-region cloud services). Choosing appropriate hosting is your responsibility. See also our [Privacy Policy](/privacy) for how LeastAction Labs handles the personal information of your account contacts.

### LeastAction Labs' Own Compliance

LeastAction Labs, Inc. complies with **BC PIPA (SBC 2003, c. 63)** for personal data collected through the marketplace website and portal. See our [Privacy Policy](/privacy) for details.

---

## Reporting a Vulnerability

If you believe you have discovered a security vulnerability in the LeastAction software or the leastactionlabs.com website, we want to hear from you. Please review our [Responsible Disclosure Policy](/vulnerability) for full details on scope, how to report, and our commitments to you.

**Security contact:** [security@leastactionlabs.com](mailto:security@leastactionlabs.com)

We ask that you do not publicly disclose a potential vulnerability before we have had an opportunity to investigate and remediate.
