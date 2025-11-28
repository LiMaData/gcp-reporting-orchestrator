# Distribution Agent Setup Guide

This guide helps you configure the credentials required for Agent 5 (Distributor) to send reports via Email and Microsoft Teams.

## 1. Email Configuration (SMTP)

We use standard SMTP to send emails via your Outlook/Office 365 account.

| Variable | Value | Description |
| :--- | :--- | :--- |
| `SMTP_SERVER` | `smtp.office365.com` | Standard Office 365 SMTP server. |
| `SMTP_PORT` | `587` | Standard TLS port. |
| `SMTP_USERNAME` | `your.email@company.com` | **Your full Outlook email address.** |
| `SMTP_PASSWORD` | `your_password` | **Your Outlook password.**<br>⚠️ *Note: If your company uses 2-Factor Authentication (2FA), you cannot use your regular password. You must generate an "App Password".* |
| `EMAIL_SENDER` | `your.email@company.com` | Usually the same as your username. |

### How to get an App Password (if 2FA is enabled):
1. Go to your Microsoft Account Security settings (https://mysignins.microsoft.com/security-info).
2. Look for "App passwords".
3. Create a new one named "GCP Orchestrator".
4. Use that generated password in `SMTP_PASSWORD`.

---

## 2. Microsoft Teams Webhook

To send notifications to a Teams channel, you need an **Incoming Webhook URL**.

### How to generate the URL:
1. Open **Microsoft Teams**.
2. Navigate to the **Channel** where you want notifications (e.g., "Marketing Ops").
3. Click the **three dots (...)** next to the channel name -> **Workflows** (or **Connectors** in older versions).
4. Search for **"Incoming Webhook"**.
5. Click **Add** and then **Configure**.
6. Give it a name (e.g., "Report Bot") and upload an icon if you want.
7. Click **Create**.
8. **Copy the URL** provided. It will look like `https://outlook.office.com/webhook/...`.
9. Paste this URL into `TEAMS_WEBHOOK_URL` in your `.env` file.

---

## 3. Recipients

These are simply the email addresses of the people who should receive the reports.

| Variable | Value | Description |
| :--- | :--- | :--- |
| `CMO_EMAIL` | `jane.doe@company.com` | The email address of the CMO (receives PDF via email). |
| `MARKETING_OPS_TEAM_CHANNEL` | `Marketing Ops` | Just a label for logs (the actual delivery goes to the Webhook URL). |
| `DATA_TEAM_GCS_NOTIFY_EMAIL` | `data.team@company.com` | (Optional) Email to notify the data team. |

---

## Summary of `.env` Configuration

Copy this into your `.env` file and fill in the blanks:

```bash
# Distribution Agent - Email (SMTP)
SMTP_SERVER=smtp.office365.com
SMTP_PORT=587
SMTP_USERNAME=your.email@company.com
SMTP_PASSWORD=your_app_password_here
EMAIL_SENDER=your.email@company.com

# Distribution Agent - Teams
TEAMS_WEBHOOK_URL=https://outlook.office.com/webhook/xxxx-xxxx-xxxx...

# Distribution Agent - Recipients
CMO_EMAIL=cmo@company.com
MARKETING_OPS_TEAM_CHANNEL=Marketing Ops
DATA_TEAM_GCS_NOTIFY_EMAIL=data.team@company.com
```
