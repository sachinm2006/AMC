# Peakwise frontend

React + TypeScript + Vite interface for the Peakwise load-forecasting project.

## Run locally

```bash
npm install
npm run dev
```

Open the local URL Vite prints. The public marketing page is `/`; choose **Open workspace** to view the operator dashboard at `/dashboard`.

The current interface uses clearly labeled illustrative values. It is not connected to Delhi SLDC feeds or the Python forecasting pipeline. The schedule comparison is an interface scenario and must not be treated as a procurement instruction.

## Build

```bash
npm run build
npm run preview
```

The dashboard is loaded as a separate route chunk. Forecast chart data are currently local preview values and should later be replaced through a documented API response contract.
