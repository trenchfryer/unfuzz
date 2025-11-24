# UnFuzz - AI-Powered Image Culling PWA

![UnFuzz Logo](./docs/logo.png)

**Focus on Photography, Not Sorting**

UnFuzz is a Progressive Web App that leverages OpenAI's Vision API to provide professional photographers with intelligent, automated image culling. Save 80% of your time by analyzing 30+ quality factors in minutes.

## 🌟 Features

- **AI-Powered Analysis**: Advanced AI evaluates sharpness, exposure, composition, facial expressions, and 30+ other factors
- **Duplicate Detection**: Automatically groups duplicates and burst sequences, selecting the best shot
- **Lightning Fast**: Process 400-800 images in minutes
- **Smart Selection**: Auto-select top images based on AI scores and quality tiers
- **Multi-Destination Export**: Export to Google Drive, local storage, or cloud
- **PWA Support**: Install on any device, works offline
- **RAW Format Support**: Handles CR2, NEF, ARW, DNG, and standard formats

## 📋 The 30+ Quality Factors

### Technical Quality (12 factors)
1. **Sharpness/Focus**: Overall image sharpness and critical focus accuracy
2. **Exposure**: Brightness, histogram, highlight/shadow management
3. **Color Accuracy**: White balance, color cast, natural saturation
4. **Noise/Grain**: ISO noise levels and digital artifacts
5. **Dynamic Range**: Tonal range utilization

### Composition (8 factors)
6. **Rule of Thirds**: Subject placement on power points
7. **Subject Placement**: Main subject positioning
8. **Framing**: Edge management and aspect ratio
9-13. Leading lines, balance, depth, negative space, perspective

### Subject Quality (10 factors)
14. **Facial Detection**: Face visibility and clarity
15. **Eye Status**: Open/closed eyes detection (critical factor)
16-23. Facial expression, body language, attention, group dynamics, motion blur, lighting, skin tones, framing

### Artistic Quality (5 factors)
24-28. Lighting quality, color harmony, emotional impact, uniqueness, professional polish

### Technical Defects & Duplicates
29-33. Critical defects detection, duplicate identification, EXIF validation, sequence analysis

## 🚀 Quick Start

### Prerequisites

- Node.js 18+ and npm
- Python 3.11+
- OpenAI API key
- Supabase account (optional, for production)

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/unfuzz.git
cd unfuzz
```

2. **Set up environment variables**
```bash
cp .env.example .env
```

Edit `.env` with your credentials:
- `OPENAI_API_KEY`: Your OpenAI API key
- `DATABASE_URL`: Your Supabase PostgreSQL connection string
- Other configuration as needed

3. **Install frontend dependencies**
```bash
cd frontend
npm install
```

4. **Install backend dependencies**
```bash
cd backend
pip install -r requirements.txt
```

5. **Set up database** (optional for production)
```bash
# Run the SQL schema in your Supabase SQL editor
cat database/schema.sql
```

6. **Run the development servers**

Terminal 1 (Backend):
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

Terminal 2 (Frontend):
```bash
cd frontend
npm run dev
```

7. **Open your browser**
```
http://localhost:3000
```

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     User Browser                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │         Next.js PWA (React + Tailwind)          │   │
│  │  - Drag & Drop Upload                           │   │
│  │  - Real-time Progress                           │   │
│  │  - Image Gallery & Review                       │   │
│  └─────────────────────────────────────────────────┘   │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTPS
┌──────────────────────▼──────────────────────────────────┐
│              FastAPI Backend Server                      │
│  - Image Upload Handler                                  │
│  - OpenAI Vision API integration                         │
│  - Perceptual hashing (duplicates)                       │
│  - Export Manager                                        │
└──────────────────────┬──────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
┌───────▼──────┐ ┌────▼─────┐ ┌─────▼────────┐
│   Supabase   │ │  OpenAI  │ │   Storage    │
│  PostgreSQL  │ │ Vision   │ │  (Local/S3)  │
└──────────────┘ └──────────┘ └──────────────┘
```

## 📁 Project Structure

```
unfuzz/
├── frontend/                 # Next.js frontend
│   ├── app/                 # App router pages
│   │   ├── page.tsx         # Landing page
│   │   └── app/
│   │       └── page.tsx     # Main culling interface
│   ├── components/          # React components
│   │   ├── ImageGallery.tsx
│   │   └── ImageDetailModal.tsx
│   ├── lib/                 # Utilities and API
│   │   ├── api.ts          # API client
│   │   └── types.ts        # TypeScript types
│   └── public/             # Static assets
│
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── main.py         # FastAPI application
│   │   ├── api/            # API routes
│   │   │   ├── images.py
│   │   │   ├── projects.py
│   │   │   └── analysis.py
│   │   ├── services/       # Business logic
│   │   │   ├── openai_vision.py
│   │   │   └── duplicate_detector.py
│   │   ├── models/         # Pydantic models
│   │   ├── core/           # Configuration
│   │   └── utils/          # Utilities
│   └── requirements.txt
│
├── database/
│   └── schema.sql          # Supabase database schema
│
├── PRD.md                  # Product Requirements Document
├── .env                    # Environment variables
└── README.md               # This file
```

## 🔧 Configuration

### Environment Variables

**Frontend (.env.local)**
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_NAME=UnFuzz
```

**Backend (.env)**
```env
OPENAI_API_KEY=your_openai_key
DATABASE_URL=postgresql://...
SUPABASE_URL=https://your-project.supabase.co
```

See `.env.example` for complete configuration options.

## 🚢 Deployment

### Frontend (Vercel)

1. Push your code to GitHub
2. Import project in Vercel
3. Set environment variables
4. Deploy

```bash
cd frontend
vercel --prod
```

### Backend (Railway/Render)

1. Create new project in Railway or Render
2. Connect your GitHub repository
3. Set environment variables
4. Deploy

```bash
# Railway
railway up

# Or use Docker
docker build -t unfuzz-backend ./backend
docker run -p 8000:8000 unfuzz-backend
```

## 🧪 Testing

```bash
# Backend tests
cd backend
pytest

# Frontend tests (when implemented)
cd frontend
npm test
```

## 📊 API Documentation

Once the backend is running, visit:
- Swagger UI: `http://localhost:8000/api/docs`
- ReDoc: `http://localhost:8000/api/redoc`

### Key Endpoints

**Projects**
- `POST /api/v1/projects` - Create new project
- `GET /api/v1/projects/{id}` - Get project details

**Images**
- `POST /api/v1/images/upload` - Upload single image
- `POST /api/v1/images/upload-batch` - Upload multiple images

**Analysis**
- `POST /api/v1/analysis/analyze/{image_id}` - Analyze single image
- `POST /api/v1/analysis/detect-duplicates` - Detect duplicates in project
- `POST /api/v1/analysis/smart-select/{project_id}` - Auto-select best images

## 🤝 Contributing

Contributions are welcome! Please read our contributing guidelines first.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- OpenAI for the Vision API
- Supabase for database and authentication
- Vercel for hosting
- The photography community for feedback

## 📧 Contact

- Website: https://unfuzz.app
- Email: support@unfuzz.app
- Twitter: @unfuzzapp

## 🗺️ Roadmap

- [ ] Video frame culling
- [ ] Custom AI model training
- [ ] Lightroom/Capture One integration
- [ ] Mobile apps (iOS/Android)
- [ ] Team collaboration features
- [ ] Advanced batch editing

## 📚 Documentation

For detailed documentation, visit:
- [Product Requirements Document](./PRD.md)
- [Database Schema](./database/schema.sql)
- [API Documentation](http://localhost:8000/api/docs)

---

**Made with ❤️ for photographers who value their time**
