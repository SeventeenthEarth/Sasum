# Sasum

A Django-based web application for fetching, filtering, and managing startup grant announcements using multiple AI providers.

> The name "Sasum" (사슴, meaning "deer" in Korean) was chosen because deer have a wide field of vision and sensitive perception - symbolizing the ability to effectively detect and identify startup grant announcements.

## Features

- Fetch announcements from the public data portal API (Korea Institute of Startup & Entrepreneurship Development)
- AI-powered filtering to find announcements matching your specific criteria using OpenAI or Gemini
- Store announcements in a PostgreSQL database
- Mark announcements as "interested" or "applied" and add personal notes
- Filter and sort stored announcements by various criteria

## Tech Stack

- **Backend**: Django 4.2
- **Frontend**: Django templates with Bootstrap 5
- **Database**: PostgreSQL 14
- **AI Integration**: 
  - OpenAI API - gpt-4o-mini
  - Google Generative AI - gemini-2.0-flash-lite
- **Deployment**: Docker and Docker Compose

## Setup Instructions

### Prerequisites

- Docker and Docker Compose
- Python 3.9+ (for local development without Docker)

### Environment Variables

Create a `.env` file in the root directory with the following variables:

```
OPENAI_API_KEY=your_openai_api_key
OPENAI_ASSISTANT_ID=yout_openai_assistant_id
GEMINI_API_KEY=your_gemini_api_key
PUBLIC_DATA_API_KEY=your_public_data_api_key
POSTGRES_DB=announcement_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=secure_password
DB_HOST=db
DB_PORT=5432
DEBUG=False
SECRET_KEY=a_secure_secret_key_for_django
```

Replace the placeholder values with your actual API keys and credentials. You don't need to provide all AI API keys - the application will work with whichever APIs you configure.

### Running with Docker

1. Build and start the containers:

```bash
docker-compose up -d
```

2. Access the application at http://localhost:8000/

### Development without Docker

1. Create a virtual environment and install dependencies:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. Update the `.env` file to use localhost for DB_HOST.

3. Run migrations:

```bash
python manage.py migrate
```

4. Start the development server:

```bash
python manage.py runserver
```

## Usage

1. **New Announcements**: Visit `/new-announcement/` to:
   - Select an AI platform (OpenAI or Gemini)
   - Choose a specific model for that platform
   - Enter your filtering condition
   - Fetch and filter new announcements

2. **Stored Announcements**: Visit `/stored-announcement/` to view and manage saved announcements.

## License

This project is licensed under the MIT License.
