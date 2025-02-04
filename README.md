# MLB Quick Recap Backend

A backend service that provides concise, multi-language summaries of MLB games using the MLB Stats API and Google's Gemini AI.

## Features

- Real-time MLB game data fetching
- AI-powered game recaps generation
- Multi-language support (English, Spanish, Japanese)
- Redis caching for improved performance
- Rate limiting for API stability

## Prerequisites

- Python 3.8 or higher
- Redis server
- Google Cloud Platform account with Gemini API access
- MLB Stats API access

## Setup

1. Clone the repository

```bash
git clone <repository-url>
cd mlb-quick-recap-backend
```

2. Create and activate a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
```

3. Install dependencies

```bash
pip install -r requirements.txt
```

4. Configure environment variables

Copy the `.env.example` file to `.env` and update the following variables:

```env
GOOGLE_GEMINI_API_KEY=your_gemini_api_key
MLB_API_BASE_URL=https://statsapi.mlb.com/api/v1
MLB_GUMBO_API_BASE_URL=https://statsapi.mlb.com/api/v1.1
MLB_SPORT_ID=1
REDIS_URL=redis://localhost:6379
```

## Running the Application

1. Start the Redis server
2. Run the application:

```bash
python main.py
```

The API will be available at `http://localhost:8000`

## API Endpoints

### Get Games List

```
GET /api/v1/games?season={year}&team_id={team_id}&page={page}&per_page={per_page}
```

Returns a paginated list of games for a specific team and season.


Generates an AI-powered recap for a specific game. Supported language codes: `en`, `es`, `ja`

## Docker Deployment

1. Build the Docker image:

```bash
docker build -t mlb-quick-recap-backend .
```

2. Run the container:

```bash
docker run -p 8000:8000 --env-file .env mlb-quick-recap-backend
```

## Cloud Run Deployment

This project includes a GitHub Actions workflow for automatic deployment to Google Cloud Run. Configure the following secrets in your GitHub repository:

- `GCP_PROJECT_ID`
- `GCP_SA_KEY`
- `GOOGLE_GEMINI_API_KEY`

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

