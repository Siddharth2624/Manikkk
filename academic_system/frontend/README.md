# Academic System - Frontend

Modern React 18 frontend for the Academic Management System with Vite, Tailwind CSS, and Radix UI components.

## Tech Stack

- **React 18.3** - UI library with hooks
- **Vite 5.1** - Fast build tool and dev server
- **React Router 6.22** - Client-side routing
- **Tailwind CSS 3.4** - Utility-first CSS framework
- **Radix UI** - Accessible component primitives
- **Lucide React** - Beautiful icon set
- **Axios** - HTTP client (fallback)
- **date-fns** - Date utilities

## Project Structure

```
src/
├── components/
│   ├── layout/
│   │   ├── layout.jsx    # Main layout wrapper with navbar
│   │   └── navbar.jsx    # Navigation bar with role-based menu
│   └── ui/               # shadcn/ui style components
│       ├── button.jsx
│       ├── card.jsx
│       ├── input.jsx
│       └── select.jsx
├── lib/
│   ├── api.js            # API helper and auth utilities
│   └── utils.js          # cn() utility for class merging
├── pages/
│   ├── login.jsx         # Login/Register page
│   ├── dashboard.jsx     # Role-based dashboard
│   ├── timetable.jsx     # Timetable grid view
│   ├── attendance.jsx    # Attendance marking (faculty/admin)
│   ├── materials.jsx     # Study materials upload/download
│   └── admin-users.jsx   # User management (admin)
├── services/
│   ├── auth.js           # Authentication API calls
│   ├── attendance.js     # Attendance API calls
│   ├── materials.js      # Materials API calls
│   ├── timetable.js      # Timetable API calls
│   └── admin.js          # Admin API calls
├── App.jsx               # Route definitions
├── main.jsx              # React entry point
└── index.css             # Global styles + Tailwind directives
```

## Getting Started

### Prerequisites

- Node.js 18+ and npm/yarn/pnpm

### Installation

```bash
cd frontend
npm install
```

### Environment Variables

Create `.env` file:

```env
VITE_API_URL=http://localhost:8000/api/v1
```

### Development

```bash
npm run dev
```

Open http://localhost:5173

### Build

```bash
npm run build
```

Output in `dist/` directory.

## Features by Role

### Student
- View personalized timetable
- Check attendance summary
- Download study materials

### Faculty
- Mark student attendance
- Upload study materials
- View timetable

### Admin
- All faculty features
- Manage users (create, edit, delete)
- View system statistics

## Design Principles

Following **ui-ux-pro-max** guidelines:

- **Accessibility**: 4.5:1 contrast minimum, keyboard navigation
- **Touch**: 44px minimum touch targets
- **Performance**: Optimized images, reduced-motion support
- **Responsive**: Mobile-first, tested at 375px-1440px
- **No emojis**: Using Lucide SVG icons instead
- **Hover states**: All interactive elements have clear feedback

## API Integration

All API calls go through `api()` helper in `lib/api.js`:
- Auto-includes JWT token from localStorage
- Handles error responses
- Type-safe JSON parsing

Example:
```javascript
import { api } from '../lib/api';

const data = await api('/timetable?semester=1&section=A');
```

## Authentication Flow

1. User enters credentials on `/login`
2. JWT token received from backend
3. Token stored in `localStorage.access_token`
4. User data stored in `localStorage.user`
5. Protected routes check for valid token
6. `api()` helper includes `Authorization: Bearer <token>` header

## Color Scheme

| Usage | Light Mode | Dark Mode |
|-------|-----------|-----------|
| Primary | Blue-600 | Blue-500 |
| Success (Present) | Green-600 | Green-500 |
| Danger (Absent/Delete) | Red-600 | Red-500 |
| Theory | Green-100 | Green-900 |
| Lab | Blue-100 | Blue-900 |
| Lunch | Yellow-100 | Yellow-900 |

## Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+

## License

MIT
