# NotebookLM Backend

Backend API cho ứng dụng NotebookLM - một hệ thống quản lý notebook thông minh với khả năng xử lý tài liệu, truy xuất thông tin và chat AI.

## 📋 Mục lục

- [Cấu trúc thư mục](#-cấu-trúc-thư-mục)
- [Yêu cầu hệ thống](#-yêu-cầu-hệ-thống)
- [Cách cài đặt và chạy](#-cách-cài-đặt-và-chạy)
- [API Endpoints](#-api-endpoints)
- [Services](#-services)

---

## 📁 Cấu trúc thư mục

```
notebooklm-backend/
├── docker-compose.yml          # Cấu hình Docker Compose
├── mount-data/                 # Dữ liệu mount cho containers
│   ├── database/               # Cấu hình PostgreSQL
│   └── redis/                  # Cấu hình Redis
├── notebooks/                  # Jupyter notebooks (development/testing)
│   └── output/
├── src/                        # Source code chính
│   ├── main.py                 # Entry point của ứng dụng FastAPI
│   ├── Dockerfile              # Dockerfile cho backend service
│   ├── requirements.txt        # Python dependencies
│   ├── .env                    # Biến môi trường
│   │
│   ├── core/                   # Cấu hình core
│   │   ├── config.py           # Cấu hình ứng dụng
│   │   ├── settings.py         # Settings và constants
│   │   └── logging.py          # Cấu hình logging
│   │
│   ├── database/               # Database layer
│   │   ├── connection.py       # Database connection
│   │   └── get_db.py           # Database session management
│   │
│   ├── models/                 # SQLAlchemy Models
│   │   ├── entities/           # Entity models
│   │   │   ├── model_user.py       # User model
│   │   │   ├── model_notebook.py   # Notebook model
│   │   │   ├── model_source.py     # Source model
│   │   │   └── model_message.py    # Message model
│   │   └── relationship/       # Relationship models
│   │       └── notebook_source.py  # Notebook-Source relationship
│   │
│   ├── routes/                 # API Routes
│   │   ├── route_user.py       # User authentication APIs
│   │   ├── route_notebook.py   # Notebook management APIs
│   │   ├── route_source.py     # Source management APIs
│   │   ├── route_message.py    # Chat/Message APIs
│   │   └── route_retrieve.py   # Document retrieval APIs
│   │
│   ├── schemas/                # Pydantic Schemas
│   │   └── user.py             # User request/response schemas
│   │
│   ├── services/               # Business Logic Layer
│   │   ├── srv_user.py         # User service
│   │   ├── srv_notebook.py     # Notebook service
│   │   ├── srv_source.py       # Source service
│   │   ├── srv_message.py      # Message service
│   │   │
│   │   ├── llm/                # LLM Integration
│   │   │   ├── srv_llm.py          # LLM service chính
│   │   │   ├── get_prompt.py       # Prompt loader
│   │   │   ├── prompts/            # Prompt templates
│   │   │   └── parsers/            # Output parsers
│   │   │
│   │   ├── qdrant/             # Vector Database
│   │   │   ├── srv_qdrant.py       # Qdrant service
│   │   │   └── data_models.py      # Data models cho Qdrant
│   │   │
│   │   └── process_document/   # Document Processing
│   │       ├── document_processor.py   # Document processor chính
│   │       └── utils/                  # Utility functions
│   │
│   ├── static/                 # Static files (uploaded documents, images)
│   │
│   ├── utils/                  # Utility functions
│   │   ├── file_utils.py       # File handling utilities
│   │   └── hash_utils.py       # Hashing utilities
│   │
│   └── logs/                   # Log files
```

---

## 💻 Yêu cầu hệ thống

- **Docker** & **Docker Compose**
- **Python 3.12+** (nếu chạy không dùng Docker)
- **PostgreSQL 15**
- **Qdrant** (Vector Database)

---

## 🚀 Cách cài đặt và chạy

### Chạy với Docker Compose (Khuyến nghị)

1. **Clone repository:**
   ```bash
   git clone <repository-url>
   cd notebooklm-backend
   ```

2. **Tạo file cấu hình môi trường:**
   
   Tạo file `mount-data/database/.env`:
   ```env
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=postgres
   POSTGRES_DB=notebook
   ```
   
   Cập nhật file `src/.env` với API keys:
   ```env
   OPENAI_API_KEY=your_openai_api_key
   GEMINI_API_KEY=your_gemini_api_key
   OPENROUTER_API_KEY=your_openrouter_api_key
   
   DATABASE_URL=postgresql+psycopg2://postgres:postgres@db:5432/notebook
   QDRANT_URL=http://qdrant:6333
   ```

3. **Khởi động tất cả services:**
   ```bash
   docker-compose up -d
   ```

4. **Kiểm tra logs:**
   ```bash
   docker-compose logs -f backend
   ```

5. **Truy cập API:**
   - Backend API: `http://localhost:4000`
   - API Documentation (Swagger): `http://localhost:4000/docs`
   - Qdrant Dashboard: `http://localhost:6333/dashboard`

### Chạy trực tiếp (Development)

1. **Cài đặt dependencies:**
   ```bash
   cd src
   pip install -r requirements.txt
   ```

2. **Cập nhật file `.env`:**
   ```env
   DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:4001/notebook
   QDRANT_URL=http://localhost:6333
   ```

3. **Chạy ứng dụng:**
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 4000 --reload
   ```

### Ports

| Service | Port |
|---------|------|
| Backend API | 4000 |
| PostgreSQL | 4001 |
| Qdrant | 6333 |

---

## 📡 API Endpoints

### 🔐 User APIs (`/api/user`)

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| `POST` | `/api/user/register` | Đăng ký tài khoản mới |
| `POST` | `/api/user/login` | Đăng nhập (trả về JWT tokens) |
| `GET` | `/api/user/me` | Lấy thông tin user hiện tại |

### 📓 Notebook APIs (`/api/notebook`)

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| `GET` | `/api/notebook` | Lấy danh sách notebooks (có phân trang) |
| `GET` | `/api/notebook/{notebook_id}` | Lấy chi tiết notebook theo ID |
| `POST` | `/api/notebook` | Tạo notebook mới (upload files PDF/DOCX) |
| `DELETE` | `/api/notebook` | Xóa notebook |

### 📄 Source APIs

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| `GET` | `/api/notebook/{notebook_id}/sources` | Lấy danh sách sources của notebook |

### 💬 Message/Chat APIs

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| `GET` | `/api/notebook/{notebook_id}/messages` | Lấy lịch sử tin nhắn |
| `GET` | `/api/notebook/{notebook_id}/rewrite` | Viết lại câu hỏi với context |
| `POST` | `/api/notebook/{notebook_id}/message` | Gửi tin nhắn và nhận phản hồi AI |

### 🔍 Retrieve APIs (`/api/retrieve`)

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| `POST` | `/api/retrieve` | Tìm kiếm tài liệu liên quan (text + images) |

---

## ⚙️ Services

### 1. LLM Service (`services/llm/`)

Quản lý tương tác với các Large Language Models:

- **Supported Providers:**
  - OpenAI (GPT models)
  - Google Gemini
  - OpenRouter

- **Chức năng:**
  - Chat completion với các prompt templates
  - Reranking documents
  - Rewrite questions với conversation context
  - Parse structured output

### 2. Qdrant Service (`services/qdrant/`)

Quản lý vector database cho semantic search:

- **Chức năng:**
  - Lưu trữ và tìm kiếm document embeddings
  - Tìm kiếm text chunks
  - Tìm kiếm images theo caption
  - Filter theo source_ids

### 3. Document Processing Service (`services/process_document/`)

Xử lý và trích xuất nội dung từ tài liệu:

- **Supported Formats:**
  - PDF (searchable & scanned)
  - DOCX
  
- **Chức năng:**
  - OCR với PaddleOCR/Docling
  - Trích xuất text và images
  - Chunking với context-aware splitting
  - Image captioning

### 4. User Service (`services/srv_user.py`)

Quản lý người dùng và authentication:

- Password hashing (bcrypt)
- JWT token generation (access + refresh)
- User authentication và authorization

### 5. Notebook Service (`services/srv_notebook.py`)

Quản lý notebooks:

- CRUD operations cho notebooks
- Phân trang notebooks theo user

### 6. Source Service (`services/srv_source.py`)

Quản lý source files:

- Upload và lưu trữ files
- Link sources với notebooks
- Trigger document processing pipeline

### 7. Message Service (`services/srv_message.py`)

Quản lý chat messages:

- Lưu trữ conversation history
- Chat với AI sử dụng retrieved context
- Format citations và responses

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| **Framework** | FastAPI |
| **Database** | PostgreSQL 15 |
| **ORM** | SQLAlchemy |
| **Vector DB** | Qdrant |
| **LLM** | OpenAI, Gemini, OpenRouter |
| **Document Processing** | Docling, PyMuPDF, PaddleOCR |
| **Embeddings** | Sentence Transformers |
| **Authentication** | JWT (python-jose) |
| **Containerization** | Docker, Docker Compose |

---

## 📝 Environment Variables

| Variable | Mô tả |
|----------|-------|
| `OPENAI_API_KEY` | OpenAI API key |
| `GEMINI_API_KEY` | Google Gemini API key |
| `OPENROUTER_API_KEY` | OpenRouter API key |
| `DATABASE_URL` | PostgreSQL connection string |
| `QDRANT_URL` | Qdrant server URL |

---

## 📄 License

MIT License
