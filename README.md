<div align="center">

<img src="rentora_project/static/img/apple-touch-icon.png" alt="Rentora Logo" width="90"/>

# Rentora

**Peer-to-Peer Tool & Equipment Rental Platform**

*List your idle tools. Rent what you need.*

[![Django](https://img.shields.io/badge/Django-6.0-092E20?logo=django&logoColor=white)](https://www.djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.14-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![MySQL](https://img.shields.io/badge/MySQL-8.0-4479A1?logo=mysql&logoColor=white)](https://www.mysql.com/)
[![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3-7952B3?logo=bootstrap&logoColor=white)](https://getbootstrap.com/)
[![Stripe](https://img.shields.io/badge/Payments-Stripe-635BFF?logo=stripe&logoColor=white)](https://stripe.com/)
[![Gemini](https://img.shields.io/badge/AI-Google_Gemini-4285F4?logo=google&logoColor=white)](https://ai.google.dev/)
[![AWS](https://img.shields.io/badge/Deployed-AWS_EC2-FF9900?logo=amazonwebservices&logoColor=white)](https://aws.amazon.com/)

</div>

---

## 📖 About

**Rentora** is a peer-to-peer marketplace — think *Airbnb, but for tools*. It connects people who own idle tools and equipment with neighbors who need them for a day or a week, instead of buying expensive gear they'll use once.

Built for the Palestinian market, where import restrictions make tools significantly more expensive than regional averages, Rentora turns idle capital sitting in homes and workshops into income for owners and affordable access for renters — powering a local sharing economy.

**Every user plays both roles:** the same account can list tools for rent *and* rent tools from others.

---

## ✨ Features

### 🛠️ Listings & Discovery
- Tool listings with categories, multi-image galleries, daily rates, deposits, and condition grades
- Browse page with category, price, and location filters — plus a mobile slide-in filter drawer
- **AI Smart Search** powered by Google Gemini — describe your task in plain language ("I want to hang shelves on a concrete wall") and get the right tools
- **AI-generated tool descriptions** — owners get professional listing copy automatically
- Wishlist to save tools for later
- Interactive location map on every tool page

### 📅 Booking Workflow
- Full rental lifecycle: **request → owner approval → payment → active rental → return → review**
- Automatic total-price calculation from the daily rate and rental period
- **Date-conflict protection** — a tool can never be double-booked
- Early-return refunds and overdue-day charges calculated automatically
- **Two-party return handshake:** the renter requests the return and the owner confirms receipt — no single side can close a rental alone, with a dispute path for disagreements

### 💳 Payments
- Stripe-hosted checkout — card payments with server-side webhook confirmation
- Signature-verified webhooks with an idempotent status transition (`payment_pending → confirmed`)
- Fallback confirmation on the success page covers webhook delays

### 💬 Real-Time Chat
- Per-booking conversations between owner and renter — no phone numbers needed
- Optimistic message sending, read receipts (✓ / ✓✓), and online presence indicators
- Message grouping, date dividers, and unread badges
- Messages inbox tab in the dashboard with previews and unread counts

### 🔔 Smart Notifications
- In-app notification center covering bookings, payments, messages, reviews, and return reminders
- Smart deduplication — chat notifications never pile up
- Every notification routes to exactly the right page when clicked

### ⭐ Trust & Reviews
- **Three-dimensional reviews:** rate the tool, the owner, and the renter — independently
- Aggregate ratings on profiles and tool pages
- Email verification for new accounts, public user profiles

### 📊 Dashboard
- Overview with earnings and activity stats
- My Tools, Booking Requests (pending / approved / rejected / completed), My Rentals, and Messages — in one place
- Fully mobile-responsive: icon-only navigation, wrapping booking rows, scrollable sub-tabs

### 🔐 Security
- Custom authentication built on `AbstractBaseUser` with **bcrypt** password hashing
- Session-based auth guards on every protected view
- Email verification and password-reset flows
- XSS-safe message rendering, CSRF protection throughout

### ⚡ Performance
- **Automatic WebP conversion** for every uploaded image — ~80% smaller files with the same visual quality
- Throttled presence tracking (max one DB write per minute per user)
- Incremental chat polling — only new messages cross the wire

---

## 📸 Screenshots

<p align="center">
  <img src="docs/screenshots/home-ai-search.png" alt="Rentora Home — AI Smart Search"/>
  <br/>
  <sub>🤖 The AI search understands natural language — <b>even colloquial Arabic</b>: "بدي اشي بقطع الشجر عشان اخذ خشب"</sub>
</p>

<table>
  <tr>
    <td width="50%">
      <b>🎯 AI Search Results</b><br/>
      <sub>Gemini understood the Arabic request above — and found the chainsaw</sub><br/><br/>
      <img src="docs/screenshots/ai-results.png"/>
    </td>
    <td width="50%">
      <b>🛠️ Tool Details & Booking</b><br/>
      <sub>Gallery, daily rate, deposit, and date selection — no charge until the owner approves</sub><br/><br/>
      <img src="docs/screenshots/tool-detail.png"/>
    </td>
  </tr>
  <tr>
    <td width="50%">
      <b>✨ AI-Assisted Listing</b><br/>
      <sub>Generate the description, detect condition, and suggest pricing — all with AI</sub><br/><br/>
      <img src="docs/screenshots/list-tools.png"/>
    </td>
    <td width="50%">
      <b>📊 Owner Dashboard</b><br/>
      <sub>Earnings, active rentals, and booking requests across their full lifecycle</sub><br/><br/>
      <img src="docs/screenshots/dashboard.png"/>
    </td>
  </tr>
</table>

<p align="center">
  <img src="docs/screenshots/chat-notifications.png" alt="Real-time chat and smart notifications"/>
  <br/>
  <sub>💬 Real-time chat with read receipts (✓✓) and online presence — 🔔 alongside smart notifications for every booking event</sub>
</p>

<p align="center">
  <img src="docs/screenshots/payment.png" width="42%" alt="Payment success"/>
  <br/>
  <sub>💳 Stripe payment confirmed — with booking summary and an emailed receipt</sub>
</p>

<p align="center">
  <b>📱 Fully Mobile-Responsive — live on a real device</b><br/><br/>
  <img src="docs/screenshots/mobile-1.png" width="30%"/>
  &nbsp;
  <img src="docs/screenshots/mobile-3.png" width="30%"/>
  &nbsp;
  <img src="docs/screenshots/mobile-2.png" width="30%"/>
</p>



---

## 🏗️ Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Django 6.0 · Python 3.14 |
| **Database** | MySQL |
| **Frontend** | Bootstrap 5.3 · Vanilla JS · Font Awesome 6 |
| **AI** | Google Gemini (smart search + listing descriptions) |
| **Payments** | Stripe Checkout + Webhooks |
| **Auth** | Custom `AbstractBaseUser` + bcrypt |
| **Media** | Pillow with automatic WebP conversion |
| **Hosting** | AWS EC2 (Ubuntu) · Gunicorn · Nginx |

---

## 📂 Project Structure

```
rentora-platform/
├── manage.py                     # Entry point (settings injects the source root)
└── rentora_project/              # Source root
    ├── rentora_project/          # Core config (settings, urls, wsgi)
    ├── templates/                # Shared base templates & partials
    ├── static/                   # Shared CSS / JS / brand assets
    ├── users/                    # Custom user model, auth, profiles
    │   ├── models.py             # AbstractBaseUser + bcrypt
    │   ├── views.py              # Register, login, profile, verification
    │   └── middleware.py         # LastSeenMiddleware (online presence)
    └── listings/                 # The marketplace app
        ├── models/               # Modular: tool, booking, review,
        │                         #   message, notification, wishlist...
        ├── views/                # Modular: browse, tool, booking,
        │                         #   chat, review, notification views
        ├── urls/                 # Modular URL configs per domain
        ├── services/             # Gemini AI services
        └── templates/listings/   # Feature templates
```

**Architecture principle — Fat Model / Lean View:** all validation and database writes live in model managers; views only orchestrate validate → act → render.

---

## 🚀 Getting Started

### Prerequisites
- Python 3.12+
- MySQL 8.0+
- A Stripe account (test mode) and a Google AI Studio API key

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/Mahmoud-B-Miqdad/rentora-platform.git
cd rentora-platform

# 2. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Linux / macOS

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
#    Create a .env file (see below)

# 5. Run migrations
python manage.py migrate

# 6. Start the development server
python manage.py runserver
```

### Environment Variables

Create a `.env` file in the project root:

```env
SECRET_KEY=your-django-secret-key
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
SITE_URL=http://127.0.0.1:8000

# Database
DATABASE_URL=mysql://user:password@localhost:3306/rentora

# Stripe (test mode)
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Google Gemini
GEMINI_API_KEY=your-gemini-api-key

# Email (verification & password reset)
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
```

---

## ☁️ Deployment (AWS EC2)

The platform runs in production on an AWS EC2 Ubuntu instance behind Nginx:

```
Internet → Nginx (reverse proxy, static files) → Gunicorn → Django → MySQL
```

Standard deployment cycle:

```bash
ssh -i rentora-key.pem ubuntu@<server-ip>
cd rentora-platform
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
sudo systemctl restart gunicorn
```

> `USE_X_FORWARDED_HOST` is enabled so absolute URLs (email verification, Stripe callbacks, OG tags) resolve to the real hostname behind the proxy.

---

## 🧠 Engineering Highlights

### The Return Handshake
Marking a rental "completed" reliably was the hardest trust problem in the project. A naive single-button design failed two ways: an owner pressing late unfairly flagged the renter as overdue, and an accidental press closed a booking while the renter still held the tool. The fix is a **two-party handshake** — the renter requests the return, the owner confirms receipt, and disagreements escalate to a dispute instead of silently completing.

### The Image Pipeline
Owners upload photos straight from their phones — often 5–8 MB each. Every upload is automatically converted to **WebP** on the server, cutting file sizes by ~80% with no visible quality loss, keeping pages fast and storage costs flat.

### Notifications That Don't Spam
A chat conversation could generate dozens of notifications. Rentora deduplicates: before creating a new-message notification, any existing one for the same conversation is removed — the bell always shows a sane count, and opening the chat clears it automatically.

---

## 🗺️ Roadmap

- **Local payments** — JawwalPay / PalPay integration + cash-on-pickup wallet, built for how Palestine actually pays
- **Deposit lifecycle** — hold on checkout, auto-refund on clean returns, deduction on disputes
- **Booking cancellation** with a fair cancellation policy and automatic refunds
- **User reporting & moderation** — report abusive profiles, staff review queue, account suspension
- **Arabic language support** — full i18n with RTL layout
- **PDF receipts** after every payment
- **Seasonal equipment** — agricultural & olive-harvest gear, a uniquely Palestinian market
- **Native mobile app** with push notifications

---

## 👥 Team

| | |
|---|---|
| **Mahmoud Miqdad** | [@Mahmoud-B-Miqdad](https://github.com/Mahmoud-B-Miqdad) |
| **Mona Alakras** | |
| **Ahmad Alshwiki** | |

---

<div align="center">

**Rentora — every tool deserves a second job.** 🔧

</div>
