# Quantum Signals - Trading Signal Dashboard

## Overview

This is a full-stack trading signal dashboard application called "Quantum Signals." It consists of two main parts:

1. **Web Dashboard** (TypeScript/React + Express): A real-time dashboard that displays trading signals with metrics like win rate, total signals, and active trades. It uses a dark trading-themed UI with live data polling.

2. **Python Trading Bot** (`trading_bot.py`): A Python script that connects to the IQ Option API (demo account only), runs technical analysis strategies (RSI, SMA crossover, MHI, Twin Towers, Pattern 23, Price Action), and sends generated signals to the web dashboard via REST API.

The bot generates signals and POSTs them to the Express server, which stores them in PostgreSQL. The React frontend polls for new signals every 5 seconds and displays them in a polished dashboard.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend (React SPA)
- **Framework**: React 18 with TypeScript, bundled by Vite
- **Routing**: wouter (lightweight client-side router)
- **State/Data**: TanStack React Query for server state management with 5-second polling interval for live signal updates
- **UI Components**: shadcn/ui (new-york style) built on Radix UI primitives with Tailwind CSS
- **Styling**: Tailwind CSS with CSS variables for a dark trading theme (custom green/red trade colors, glassmorphism effects)
- **Animations**: framer-motion for signal list animations
- **Key Pages**: Single-page dashboard at `/` showing metric cards, signal history table, and console instructions
- **Path Aliases**: `@/` maps to `client/src/`, `@shared/` maps to `shared/`

### Backend (Express API)
- **Framework**: Express 5 on Node.js with TypeScript (run via tsx)
- **API Design**: REST endpoints defined in `shared/routes.ts` with Zod schemas for validation. The routes object is shared between client and server for type safety.
- **Endpoints**:
  - `GET /api/signals` - List all signals
  - `POST /api/signals` - Create a new signal (used by the Python bot)
  - `DELETE /api/signals` - Clear all signal history
- **Dev Server**: Vite dev server middleware in development, static file serving in production
- **Build**: Custom build script using esbuild for server and Vite for client, outputs to `dist/`

### Database
- **Database**: PostgreSQL (required, connection via `DATABASE_URL` env var)
- **ORM**: Drizzle ORM with drizzle-zod for schema-to-validation integration
- **Schema**: Single `signals` table with fields: id, asset, action (CALL/PUT), strategy, confidence, timestamp, result (WIN/LOSS/PENDING), price, assetType (Normal/OTC), volatility, probability
- **Migrations**: Managed via `drizzle-kit push` (schema push approach, not migration files)

### Python Trading Bot
- **Purpose**: Standalone Python script that connects to IQ Option's unofficial API, performs technical analysis, and sends signals to the Express API
- **Dependencies**: iqoptionapi, pandas, pandas_ta, numpy, requests
- **Strategies**: RSI, SMA crossover, combined, MHI, Twin Towers, Pattern 23, Price Action
- **Integration**: Sends signals via HTTP POST to `http://localhost:5000/api/signals`
- **Note**: This is a secondary component; the primary application is the web dashboard. The bot is meant to be run separately in the shell.

### Shared Code (`shared/`)
- `schema.ts` - Drizzle table definitions and Zod insert schemas, shared between frontend and backend
- `routes.ts` - API route definitions with paths, methods, and Zod validation schemas, used by both client hooks and server route handlers

### Key Design Decisions
- **Shared route contracts**: The `shared/routes.ts` file defines API paths and validation schemas once, consumed by both the Express server and React Query hooks. This ensures type-safe API calls without code generation.
- **Polling over WebSockets**: The frontend uses 5-second polling (`refetchInterval: 5000`) rather than WebSockets for simplicity, since signal frequency is relatively low.
- **Schema push over migrations**: Uses `drizzle-kit push` for database schema management, which is simpler for development but means schema changes are applied directly.
- **Monorepo structure**: Client, server, and shared code coexist in one repo with TypeScript path aliases for clean imports.

## External Dependencies

### Required Services
- **PostgreSQL Database**: Required. Connection string must be in `DATABASE_URL` environment variable. Used for storing trading signals via Drizzle ORM.

### Key NPM Packages
- **drizzle-orm** + **drizzle-zod** + **drizzle-kit**: Database ORM, validation, and schema management
- **express** v5: HTTP server framework
- **@tanstack/react-query**: Async state management for the frontend
- **vite** + **@vitejs/plugin-react**: Frontend build tooling
- **zod**: Runtime validation for API inputs/outputs
- **wouter**: Lightweight client-side routing
- **framer-motion**: Animation library for signal list
- **shadcn/ui ecosystem**: Radix UI primitives, class-variance-authority, tailwind-merge, clsx
- **date-fns**: Date formatting for signal timestamps
- **lucide-react**: Icon library

### Python Dependencies (for trading bot)
- **iqoptionapi**: Unofficial IQ Option API client
- **pandas** + **pandas_ta**: Data analysis and technical indicators
- **numpy**: Numerical computations
- **requests**: HTTP client for sending signals to the Express API

### Replit-specific
- **@replit/vite-plugin-runtime-error-modal**: Error overlay in development
- **@replit/vite-plugin-cartographer**: Replit dev tooling
- **@replit/vite-plugin-dev-banner**: Dev environment banner