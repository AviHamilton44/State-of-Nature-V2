# Render Deployment Instructions

To deploy the State of Nature backend on Render, follow these steps:

## Option 1: Automatic Deployment (Blueprint)
I have created a `render.yaml` file in the root directory. You can use this to deploy both the backend and database at once:
1. Go to **Blueprints** in the Render Dashboard.
2. Connect your repository.
3. Render will automatically detect `render.yaml` and set everything up.

## Option 2: Manual Deployment
If you prefer to set it up manually:
- Connect your GitHub repository.
- Select the `main` branch.
- Set the **Root Directory** to `./` (if your server folder is in the root).
- **Runtime**: `Python`

## 2. Configure Build & Start Commands
- **Build Command**: `pip install -r server/requirements.txt`
- **Start Command**: `gunicorn -w 4 -k uvicorn.workers.UvicornWorker server.main:app`

## 3. Environment Variables
Add the following variables in the Render Dashboard:
- `PORT`: `8001` (or leave blank for Render's default 10000)
- `ENVIRONMENT`: `production`
- `DATABASE_URL`: Your PostgreSQL connection string.
- `GOOGLE_APPLICATION_CREDENTIALS`: Path to your GEE key (if uploading to Render disk) or use a secret file.

## 4. Health Check
- Render will automatically use the `/health` endpoint if configured.

## Local Run Command
To test locally from the root directory:
```bash
python -m uvicorn server.main:app --reload --port 8001
```
