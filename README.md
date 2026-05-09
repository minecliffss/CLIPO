# CLIPO

<p align="center">
  <img src="https://ibb.co/zhfJ6wc7" alt="CLIPO Banner" width="100%" />
</p>

<p align="center">
  <strong>AI-powered photo gallery with semantic search</strong>
</p>

<p align="center">
  Search your photos using natural language instantly.
</p>

---

## Features

- Pinterest-style masonry gallery
- AI-ready semantic photo search
- Real-time image loading
- Dark and light theme support
- Fullscreen image lightbox
- Responsive modern UI
- DM Sans typography
- Collapsible navigation sidebar
- Skeleton loading animations
- Zero-gap masonry layout

---

## Project Structure

```bash
clipo/
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   ├── components/
│   │   └── lib/
│   └── public/
│
└── backend/
    ├── server.js
    └── package.json
```

---

## Quick Start

### Clone Repository

```bash
git clone git@github.com:minecliffss/CLIPO.git
cd CLIPO
```

---

## Install Dependencies

```bash
npm install
npm run install:all
```

---

## Start Development Server

```bash
npm run dev
```

### Local Servers

| Service | URL |
|----------|------|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:3001 |

---

## Run Separately

### Backend

```bash
cd backend
npm start
```

### Frontend

```bash
cd frontend
npm run dev
```

---

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/images` | Fetch all image metadata |
| `GET /api/health` | API health status |
| `GET /images/:filename` | Serve image files |

---

## Tech Stack

### Frontend

- Next.js 16
- React 19
- TypeScript
- Tailwind CSS v4
- shadcn/ui
- next-themes

### Backend

- Express.js
- Node.js
- image-size

---

## Vision

CLIPO is designed to become an intelligent AI-powered gallery platform where users can:

- Search photos using natural language
- Organize memories automatically
- Find images instantly with AI embeddings
- Build searchable personal media libraries

---

## Future Plans

- CLIP AI semantic embeddings
- Natural language image search
- Face recognition and grouping
- Cloud synchronization
- Desktop application with Tauri
- Video indexing support
- OCR text search in images

---

## License

MIT License

---

<p align="center">
  Built with Next.js and Express
</p>
