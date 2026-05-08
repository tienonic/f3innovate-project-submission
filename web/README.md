# F3 Orchard Stress Web App

This Vercel app is the field-facing quick start for the F3 Innovate orchard stress submission.

Live app: https://f3-orchard-stress-web.vercel.app

## Local Development

```powershell
npm install
npm run dev
```

## Build

```powershell
npm run build
```

## Deploy

Run from this `web` folder:

```powershell
vercel deploy
vercel deploy --prod
```

The app uses Leaflet with OpenStreetMap tiles for the map display and Google Maps direction URLs for navigation. No Google Maps API key is required.
