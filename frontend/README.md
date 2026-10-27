# Quick_Doc Frontend

Responsive prototype for the Quick_Doc academic trust and credential verification platform.

## Run locally

```bash
cd frontend
npm install
npm run dev
```

Open the local Vite URL shown in the terminal. Build with `npm run build`.

## Included screens

- Public landing page and Central / State Vault network explainer
- Role selection and prototype sign-in
- AICTE command centre overview
- Vault network, student records search, batch upload validation preview
- Consent-led verification request preview
- Reports, audit trail and student credentials portal

## Important prototype boundaries

All metrics and records shown are illustrative. Login does not authenticate a user. File selection is local only, records and verification requests are not persisted, and no real student data is queried. Production readiness requires a backend identity provider, server-side role enforcement, API integration, consent and OTP services, secure document storage, and append-only audit persistence. Never place production secrets in frontend environment variables.
