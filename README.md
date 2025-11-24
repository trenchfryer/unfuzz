# UnFuzz - AI-Powered Image Culling & Enhancement

![UnFuzz Logo](./docs/logo.png)

**Focus on Photography, Not Sorting**

UnFuzz is a cutting-edge Progressive Web App that leverages Google's Gemini Vision AI to provide professional photographers with intelligent, automated image culling and enhancement. Save 80% of your time by analyzing 30+ quality factors and getting AI-powered enhancement recommendations in minutes.

## 🌟 Features

- **AI-Powered Analysis**: Google Gemini Vision AI evaluates sharpness, exposure, composition, facial expressions, and 30+ other factors
- **Smart Enhancement**: AI-powered post-processing recommendations with before/after preview
- **EXIF Metadata Display**: View camera settings (ISO, aperture, shutter speed, focal length, lens info)
- **Duplicate Detection**: Automatically groups duplicates and burst sequences using perceptual hashing
- **Lightning Fast**: Process hundreds of images in minutes with async processing
- **Real-time Progress**: Live upload and analysis progress tracking
- **Smart Selection**: Auto-select top images based on AI scores and quality tiers
- **PWA Support**: Modern web app that works on any device
- **RAW Format Support**: Handles CR2, NEF, ARW, DNG, HEIC, and standard formats

## 📋 The 30+ Quality Factors

### Technical Quality (12 factors)
1. **Sharpness/Focus**: Overall image sharpness and critical focus accuracy
2. **Exposure**: Brightness, histogram, highlight/shadow management
3. **Color Accuracy**: White balance, color cast, natural saturation
4. **Noise/Grain**: ISO noise levels and digital artifacts
5. **Dynamic Range**: Tonal range utilization
6-12. Contrast, clarity, chromatic aberration, vignetting, distortion, resolution, sensor dust

### Composition (8 factors)
13. **Rule of Thirds**: Subject placement on power points
14. **Subject Placement**: Main subject positioning
15. **Framing**: Edge management and aspect ratio
16-20. Leading lines, balance, depth, negative space, perspective

### Subject Quality (10 factors)
21. **Facial Detection**: Face visibility and clarity
22. **Eye Status**: Open/closed eyes detection (critical rejection factor)
23-30. Facial expression, body language, attention, group dynamics, motion blur, lighting, skin tones, framing

### Artistic Quality (4 factors)
31-34. Lighting quality, color harmony, emotional impact, uniqueness, professional polish

## 🏗️ Tech Stack

### Frontend
- **Next.js 16.0.3** with Turbopack (next-gen bundler)
- **React 18** with modern Hooks
- **TypeScript** for type safety
- **Tailwind CSS** for styling
- **@headlessui/react** for accessible UI components
- **@heroicons/react** for icons
- **react-dropzone** for drag & drop uploads
- **Axios** for HTTP requests

### Backend
- **FastAPI** - Modern Python web framework
- **Uvicorn** with auto-reload
- **Google Gemini Vision API** (gemini-1.5-flash)
- **Pillow (PIL)** for image processing
- **Pydantic** for data validation
- **aiofiles** for async file I/O

### Processing
- **Image Enhancement**: Exposure, contrast, saturation, sharpness adjustments
- **Perceptual Hashing**: dhash & phash for duplicate detection
- **EXIF Extraction**: Camera metadata parsing
- **Thumbnail Generation**: Fast preview loading
- **Batch Processing**: Parallel image analysis

## 🚀 Quick Start

### Prerequisites

- **Node.js 18+** and npm
- **Python 3.9+**
- **Micromamba** or conda (recommended)
- **Google Gemini API key** ([Get one here](https://makersuite.google.com/app/apikey))

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/unfuzz.git
cd unfuzz
```

2. **Set up Python environment**
```bash
# Using micromamba (recommended)
micromamba create -n unfuzz python=3.9
micromamba activate unfuzz

# Or using conda
conda create -n unfuzz python=3.9
conda activate unfuzz
```

3. **Install backend dependencies**
```bash
cd backend
pip install -r requirements.txt
```

4. **Install frontend dependencies**
```bash
cd ../frontend
npm install
```

5. **Set up environment variables**

Create `backend/.env`:
```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-1.5-flash
VISION_PROVIDER=gemini
UPLOAD_FOLDER=./uploads
ALLOWED_EXTENSIONS=[".jpg", ".jpeg", ".png", ".heic", ".cr2", ".nef", ".arw", ".dng"]
MAX_FILE_SIZE=52428800
```

Create `frontend/.env.local`:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_NAME=UnFuzz
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

## 🎯 Usage

1. **Upload Images**: Drag and drop or click to select images (JPG, PNG, RAW formats)
2. **Automatic Analysis**: AI analyzes each image across 30+ factors
3. **Review Results**: View scores, detected issues, and recommendations
4. **View Details**: Click any image to see:
   - Overall score and quality tier
   - Individual factor scores
   - EXIF metadata (camera settings)
   - AI recommendations
   - Enhancement preview
5. **Enhance Images**: Preview and download AI-enhanced versions
6. **Export**: Select and export your best shots

## 📁 Project Structure

```
unfuzz/
├── frontend/                      # Next.js frontend
│   ├── app/                       # App router pages
│   │   ├── page.tsx              # Landing page
│   │   └── app/
│   │       └── page.tsx          # Main application
│   ├── components/               # React components
│   │   ├── ImageGallery.tsx
│   │   ├── ImageDetailModal.tsx
│   │   └── EnhancementPreviewModal.tsx
│   ├── lib/                      # Utilities
│   │   ├── api.ts               # API client
│   │   └── types.ts             # TypeScript interfaces
│   └── public/                   # Static assets
│
├── backend/                       # FastAPI backend
│   ├── app/
│   │   ├── main.py              # FastAPI app
│   │   ├── api/                 # API routes
│   │   │   ├── images.py        # Upload endpoints
│   │   │   ├── analysis.py      # Analysis endpoints
│   │   │   ├── enhancement.py   # Enhancement endpoints
│   │   │   └── projects.py      # Project management
│   │   ├── services/            # Business logic
│   │   │   ├── gemini_vision.py # Gemini AI integration
│   │   │   ├── image_enhancement.py
│   │   │   └── duplicate_detector.py
│   │   ├── models/              # Pydantic models
│   │   │   └── image.py
│   │   ├── core/                # Configuration
│   │   │   └── config.py
│   │   └── utils/               # Utilities
│   │       └── image_processing.py
│   ├── uploads/                 # Uploaded images
│   │   └── thumbnails/         # Generated thumbnails
│   └── requirements.txt
│
├── PRD.md                        # Product Requirements
└── README.md                     # This file
```

## 🔧 Configuration

### Backend Environment Variables

```env
# AI Provider
GEMINI_API_KEY=your_api_key          # Required: Google Gemini API key
GEMINI_MODEL=gemini-1.5-flash        # Model to use
VISION_PROVIDER=gemini               # AI provider (gemini or openai)

# Storage
UPLOAD_FOLDER=./uploads              # Image storage location
MAX_FILE_SIZE=52428800              # Max file size (50MB)

# Allowed Formats
ALLOWED_EXTENSIONS=[".jpg", ".jpeg", ".png", ".heic", ".cr2", ".nef", ".arw", ".dng"]

# CORS
CORS_ORIGINS=["http://localhost:3000"]
```

### Frontend Environment Variables

```env
NEXT_PUBLIC_API_URL=http://localhost:8000    # Backend API URL
NEXT_PUBLIC_APP_NAME=UnFuzz                  # App name
```

## 📊 API Documentation

Once the backend is running, visit:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

### Key Endpoints

**Images**
- `POST /api/v1/images/upload` - Upload single image
- `POST /api/v1/images/upload-batch` - Upload multiple images
- `GET /api/v1/images/{image_id}` - Get image details

**Analysis**
- `POST /api/v1/analysis/analyze/{image_id}` - Analyze image with AI
- `POST /api/v1/analysis/detect-duplicates` - Detect duplicate images
- `GET /api/v1/analysis/analyze-batch` - Batch analysis

**Enhancement**
- `GET /api/v1/enhancement/preview/{image_id}` - Get enhancement preview
- `GET /api/v1/enhancement/enhance/{image_id}` - Download enhanced image
- `GET /api/v1/enhancement/{image_id}/can-enhance` - Check if enhancement available

**Health**
- `GET /health` - Health check

## 🎨 Features in Detail

### AI Analysis
- **30+ Quality Factors**: Comprehensive image evaluation
- **Quality Tiers**: excellent, good, acceptable, poor, reject
- **Rejection Criteria**: Automatically flags images with closed eyes, severe blur, etc.
- **Context-Aware**: Uses EXIF data for intelligent recommendations

### Camera Settings Recommendations
- **ISO Guidance**: Optimal ISO for lighting conditions
- **Aperture Advice**: Best f-stop for subject type
- **Shutter Speed**: Recommended speeds for motion/stillness
- **Focal Length**: Ideal lens choices

### Post-Processing Recommendations
- **Exposure Adjustments**: EV compensation values
- **Contrast Enhancement**: Specific adjustment amounts
- **Saturation Tuning**: Color intensity recommendations
- **Sharpening**: Unsharp mask parameters
- **Auto-fix Eligibility**: Whether automated enhancement will help

### Enhancement Preview
- **Before/After Comparison**: Side-by-side view
- **Real-time Preview**: See changes before downloading
- **Adjustment Details**: View specific values applied
- **Download Options**: Local download or Google Drive (coming soon)

## 🚢 Deployment

### Frontend (Vercel)

```bash
cd frontend
vercel --prod
```

Set environment variables in Vercel dashboard:
- `NEXT_PUBLIC_API_URL` - Your backend URL

### Backend (Railway/Render/AWS)

**Using Railway:**
```bash
railway up
```

**Using Docker:**
```bash
cd backend
docker build -t unfuzz-backend .
docker run -p 8000:8000 --env-file .env unfuzz-backend
```

## 🧪 Testing

```bash
# Backend - Test single endpoint
curl http://localhost:8000/health

# Upload test image
curl -X POST -F "file=@test.jpg" http://localhost:8000/api/v1/images/upload

# Frontend - Check build
cd frontend
npm run build
```

## 🐛 Troubleshooting

**Port 8000 already in use:**
```bash
lsof -ti:8000 | xargs kill
```

**Module not found errors:**
```bash
cd backend && pip install -r requirements.txt
cd frontend && npm install
```

**CORS errors:**
- Ensure `CORS_ORIGINS` in backend config includes your frontend URL
- Check `NEXT_PUBLIC_API_URL` in frontend `.env.local`

## 🗺️ Roadmap

### Coming Soon
- [x] AI-powered image analysis
- [x] Enhancement preview with before/after
- [x] EXIF metadata display
- [x] Duplicate detection
- [ ] Google Drive integration
- [ ] Batch enhancement
- [ ] Project management
- [ ] Export to Lightroom/Capture One

### Future Features
- [ ] Video frame culling
- [ ] Custom AI model training
- [ ] Mobile apps (iOS/Android)
- [ ] Team collaboration
- [ ] Advanced filtering and sorting
- [ ] Cloud storage integration (Dropbox, OneDrive)

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **Google Gemini** for the powerful Vision AI API
- **Vercel** for Next.js and hosting
- **FastAPI** for the amazing Python web framework
- The photography community for valuable feedback

## 📧 Contact

- Website: https://unfuzz.app (coming soon)
- Email: support@unfuzz.app
- GitHub: [@yourusername](https://github.com/yourusername)

## 🎯 Performance

- **Analysis Speed**: 15-25 seconds per image (Gemini API)
- **Batch Processing**: Parallel processing for multiple images
- **Thumbnail Generation**: < 100ms per image
- **Memory Efficient**: Images resized to 2048px for API processing
- **Storage**: Minimal - only uploads and thumbnails stored locally

## 💡 Tips for Best Results

1. **Upload High-Quality Images**: Better source = better analysis
2. **Include EXIF Data**: Camera settings help AI provide better recommendations
3. **Batch Upload**: Upload all similar images together for better duplicate detection
4. **Review AI Suggestions**: AI is smart but your artistic vision matters
5. **Use Enhancement Preview**: Always preview before downloading enhanced versions

---

**Built with ❤️ for photographers who value their time**

*Powered by Google Gemini Vision AI, Next.js 16, FastAPI, and modern web technologies*
