# Cookie Policy

**Last Updated: March 2026**

---

## Introduction

This Cookie Policy explains how LeastAction Labs, Inc. ("LeastAction Labs," "we," "us," or "our"), a company incorporated under the Canada Business Corporations Act (R.S.C., 1985, c. C-44), with its registered office in British Columbia, Canada, uses cookies and similar technologies on the leastactionlabs.com website and marketplace portal (the "Website").

This policy also explains cookies set by **your self-hosted LeastAction deployment** — an important distinction described below.

For more information about how we handle personal information generally, see our [Privacy Policy](/privacy).

---

## What Are Cookies?

Cookies are small text files that a website places on your browser or device when you visit. They allow the website to remember information about your visit, such as your session state or preferences. Cookies may be:

- **Session cookies:** Deleted automatically when you close your browser
- **Persistent cookies:** Remain on your device for a set period or until you delete them
- **First-party cookies:** Set by the website you are visiting (in this case, leastactionlabs.com)
- **Third-party cookies:** Set by a domain other than the website you are visiting

---

## Part 1: Cookies on the leastactionlabs.com Website

LeastAction Labs controls the cookies set on the leastactionlabs.com website and marketplace portal. We use the following categories of cookies:

### 1.1 Essential Cookies

Essential cookies are necessary for the Website to function. They do not require your consent under BC PIPA or PIPEDA because they are strictly necessary to deliver a service you have requested.

These cookies enable:
- User session management (keeping you logged in to the portal while you navigate)
- CSRF (Cross-Site Request Forgery) protection tokens, which protect the security of form submissions
- Storing your cookie consent preference so we do not ask you again unnecessarily

### 1.2 Analytics Cookies

We use privacy-respecting website analytics to understand how visitors use the Website and to improve it. Our analytics tooling is configured to:

- Not track you across other websites
- Not build advertising or behavioural profiles
- Anonymize or pseudonymize IP addresses before storage
- Not share data with advertising networks

Analytics cookies collect information such as: pages visited, time on page, referrer URL, browser type, and operating system. This data is aggregated and does not identify you as an individual.

Under BC PIPA and PIPEDA, we rely on **implied consent** for essential cookies and seek **express consent** (via our cookie consent banner) for analytics cookies. You may decline analytics cookies without affecting your ability to use the Website.

### 1.3 Advertising and Marketing Cookies

We do **not** currently use advertising or marketing cookies on the Website. We are not connected to any third-party advertising networks or retargeting platforms. If this changes in the future, we will update this policy and update our consent banner before placing any such cookies.

---

## Cookie Table — leastactionlabs.com Website

The following cookies may be set on your device when you visit the Website:

| Cookie Name | Purpose | Duration | Type |
|---|---|---|---|
| `la_session` | Maintains your authenticated session with the LeastAction Labs portal. Allows you to stay logged in as you navigate the marketplace and account pages. | Session (deleted when browser closes) | Essential, First-Party |
| `la_csrf` | CSRF protection token. Used to verify that form submissions (e.g., account creation, subscription changes) originate from the legitimate Website and not a malicious third party. | Session | Essential, First-Party |
| `la_consent` | Stores your cookie consent preference (accepted / declined analytics) so that we do not prompt you on every page visit. | 12 months | Essential, First-Party |
| `la_analytics` | Used by our privacy-respecting analytics platform to count page visits and understand navigation patterns. IP addresses are anonymized. No cross-site tracking. | 30 days | Analytics, First-Party |

We will update this table if we add or remove cookies. Material changes will be accompanied by an updated "Last Updated" date and, where required, an updated consent notice.

---

## Part 2: Cookies in Your Self-Hosted LeastAction Deployment

This section is important if you operate a self-hosted LeastAction instance.

**LeastAction Labs does not control cookies set by your self-hosted LeastAction deployment.** When you or your end users access a LeastAction instance that you operate on your own infrastructure, cookies are set by your deployment, not by LeastAction Labs.

The LeastAction application sets the following types of cookies on your deployed instance:

- **Session cookies:** Used to maintain authenticated sessions for users of your LeastAction deployment. Marked `HttpOnly` and `SameSite=Strict` by the application.
- **CSRF tokens:** Used to protect API requests and form submissions within your deployment.

**If you operate a self-hosted LeastAction deployment, you are the data controller** for all cookies and data processed by that instance. You are responsible for:

- Determining whether your deployment collects personal data through cookies
- Complying with applicable privacy and cookie consent laws in your jurisdiction (including PIPEDA, GDPR, ePrivacy Directive, or other applicable laws)
- Providing your own cookie notice and consent mechanism to end users of your deployment, if required by applicable law
- Configuring your deployment appropriately (e.g., setting the `Secure` flag on cookies via your reverse proxy configuration if you are serving over HTTPS)

LeastAction Labs has no visibility into, and accepts no responsibility for, cookie practices on self-hosted customer deployments.

---

## Managing Cookies

### Browser Settings

Most web browsers allow you to control cookies through their settings. You can typically:

- View the cookies stored on your device
- Delete individual cookies or all cookies
- Block cookies from specific websites
- Block all third-party cookies
- Receive a notification when a cookie is set

Blocking essential cookies may affect the functionality of the Website (for example, you may not be able to log in to the portal). Blocking analytics cookies does not affect your ability to use the Website.

For guidance on managing cookies in your browser, refer to your browser's help documentation:
- [Google Chrome](https://support.google.com/chrome/answer/95647)
- [Mozilla Firefox](https://support.mozilla.org/en-US/kb/enable-and-disable-cookies-website-preferences)
- [Safari](https://support.apple.com/en-ca/guide/safari/sfri11471/mac)
- [Microsoft Edge](https://support.microsoft.com/en-us/microsoft-edge/delete-cookies-in-microsoft-edge-63947406-40ac-c3b8-57b9-2a946a29ae09)

### Consent Banner

When you first visit the Website, you will see a cookie consent banner. You may accept or decline non-essential (analytics) cookies. You can change your preference at any time by clearing the `la_consent` cookie in your browser settings, which will cause the consent banner to appear again on your next visit.

---

## BC PIPA and PIPEDA

LeastAction Labs processes cookie-related data in compliance with:

- **BC PIPA (SBC 2003, c. 63):** We rely on **implied consent** for essential cookies that are necessary to deliver the service. We obtain **express consent** (via the cookie consent banner) for analytics cookies.
- **PIPEDA (SC 2000, c. 5):** We apply the same consent standards for interprovincial and international visitors.

You may withdraw consent for analytics cookies at any time using your browser settings or by adjusting your consent preference through the banner. Withdrawal of consent for analytics cookies does not affect the lawfulness of processing before withdrawal.

---

## Changes to This Cookie Policy

We may update this Cookie Policy from time to time. We will post the updated policy on this page and update the "Last Updated" date. For material changes, we will provide at least **30 days' advance notice** consistent with our [Privacy Policy](/privacy).

---

## Contact

For questions about our use of cookies:

**LeastAction Labs, Inc.**
Email: [privacy@leastactionlabs.com](mailto:privacy@leastactionlabs.com)
Web: [https://leastactionlabs.com/contactus](/contactus)
