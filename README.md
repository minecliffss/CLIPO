# Lensora Gallery

A full-stack photo gallery web app with Pinterest-style masonry layout.

## Project Structure

```
lensora-gallery-new/
├── frontend/          # Next.js + shadcn/ui frontend
│   ├── src/
│   │   ├── app/       # Next.js app router pages
│   │   ├── components/# React components
│   │   └── lib/       # Utilities
│   └── public/        # Static assets
│
└── backend/           # Express.js API server
    ├── server.js      # Main server file
    └── package.json
```

## Features

- **Pinterest-style masonry grid** with real image aspect ratios
- **Search bar** (centered in top navbar)
- **Collapsible left sidebar** with navigation
- **Image lightbox** - click any image to open full view with prev/next
- **Dark/light theme toggle**
- **Skeleton loading** while images load
- **DM Sans** font
- **0px gap** between images

## Quick Start

### Option 1: Start both at once (from root)

```bash
cd /home/daniel/Desktop/Lensora/lensora-gallery-new

# First time only
npm install
npm run install:all

# Start both frontend and backend
npm run dev
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:3001

### Option 2: Start separately

**Terminal 1 - Backend:**
```bash
cd /home/daniel/Desktop/Lensora/lensora-gallery-new/backend
npm start
```

**Terminal 2 - Frontend:**
```bash
cd /home/daniel/Desktop/Lensora/lensora-gallery-new/frontend
npm run dev
```

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/images` | List all images with dimensions |
| `GET /api/health` | Health check |
| `GET /images/:filename` | Serve image file |

## Tech Stack

**Frontend:** Next.js 16, React 19, TypeScript, Tailwind CSS v4, shadcn/ui, next-themes

**Backend:** Express.js, Node.js, image-size
