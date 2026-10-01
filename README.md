# Niken Ecoprint — Website Prototype

Website prototype for **Niken Ecoprint by PT. Manna Borneo Persada** (Balikpapan, East Kalimantan), built from
[`docs/Blueprint_Website_Niken_Ecoprint_CMS.md`](docs/Blueprint_Website_Niken_Ecoprint_CMS.md) (Blueprint v1, 1 Oct 2026).

**Status:** Stage 2 prototype (design & flow review). Retail prices are examples and payments are simulated.
Data is stored in the visitor's browser (`localStorage`); a real backend and database are the next stage.

## What's inside

| Path | Contents |
| --- | --- |
| `index.html` | The whole site: storefront (EN/ID), cart & checkout, B2B inquiry, digital catalogue, Admin CMS |
| `img/` | Product, process and exhibition photos taken from the company profile, catalogue and product cards |
| `docs/` | Website blueprint |
| `uat/uat.py` | End-to-end UAT suite (Playwright, 61 scenarios) |
| `uat/results.json` | Latest UAT results — 61/61 passed |

## Run locally

```bash
python3 -m http.server 8000
# open http://localhost:8000
```

Admin CMS: footer → **Admin CMS**, then choose a role (Owner, Content Admin, Sales, Fulfillment).

## Run the UAT

```bash
pip install playwright && python3 -m playwright install chromium
python3 uat/uat.py
```

## Features

- Storefront: home with animated hero and quiet forest/stream ambience (starts on first tap, can be muted),
  shop with filter/search/sort, product detail with *exact piece* vs *pattern family* mode, made-to-order rules
- Checkout: server-side price calculation, 15-minute stock reservation, simulated payment callbacks
  (success, failed, expired, duplicate, late payment → reconciliation)
- B2B: wholesale/export/custom/private-label inquiries with numbered confirmation, quotation versions
- Admin CMS: products, variants & pieces, draft → preview → publish, orders & fulfilment, inquiries & quotations,
  content & contacts, catalogue versions, reports & CSV, settings & audit log, role-based permissions
- Accessibility: keyboard navigation, skip link, labelled forms, dark mode, reduced motion

## Before going live (blueprint §16–18)

- Backend + database (e.g. Supabase), real admin login with MFA, server-side permissions
- Payment gateway with signed webhooks, courier rates, email notifications, PDF catalogue export, backups
- Owner-approved data: retail prices, active WhatsApp number, return policy, size charts, real hero photo
