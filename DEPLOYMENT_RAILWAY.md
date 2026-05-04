# Deploying CodeScribe to Railway

This guide walks through deploying CodeScribe to Railway for public access.

## Prerequisites

- GitHub account
- Railway account (free tier)
- Your Google Gemini API key from `.env`

## Quick Start (5 minutes)

### Step 1: Sign Up for Railway
1. Go to [railway.app](https://railway.app)
2. Click "Start Now"
3. Sign in with GitHub

### Step 2: Create New Project
1. Click "Create Project"
2. Select "Deploy from GitHub repo"
3. Find and select `ayan70747-source/CodeScribe2`
4. Click "Deploy"

Railway will auto-detect your `Procfile` and `requirements.txt` and start building.

### Step 3: Configure Environment Variables
**This is the critical step!**

1. After clicking Deploy, go to the "Variables" tab in the Railway dashboard
2. Add the following environment variables:

| Variable | Value |
|----------|-------|
| `GEMINI_API_KEY` | Your API key from `.env` |
| `FLASK_SECRET_KEY` | Generate something secure or copy from your `.env` |
| `PORT` | `3000` |
| `FLASK_DEBUG` | `false` |

**Example for GEMINI_API_KEY:**
```
AIzaSyDUupMKAXNwuWz-greZW0DHQCJfW-7CrCY
```

### Step 4: Deploy
1. Click the "Deploy" button
2. Wait for the build to complete (2-3 minutes)
3. Once deployed, Railway will show you a public URL like:
   ```
   https://codescribe-production.up.railway.app
   ```

### Step 5: Share with Your Professor
Send them the generated URL! They can access it immediately without any installation.

## After Deployment

### Set Domain (Optional)
- Go to Settings tab → Domains
- Add a custom domain if desired

### Monitor Logs
- Click "Logs" tab to see real-time activity
- Helps debug any issues

### Redeploy
- Any `git push` to `main` branch automatically redeploys
- No manual steps needed

## Troubleshooting

**Issue: "GEMINI_API_KEY not found"**
- Solution: Check Variables tab and ensure `GEMINI_API_KEY` is set exactly as shown above

**Issue: 500 Errors on API calls**
- Check Logs tab for detailed error messages
- Verify API key is active in Google Cloud Console

**Issue: Build fails**
- Railway auto-detected settings should work
- Check build logs if something went wrong

## Free Tier Details

Railway gives $5/month credits:
- This covers ~200 hours of service (more than enough for testing)
- Perfect for professor evaluation
- Upgrade anytime if needed

## Environment Variable Reference

```
GEMINI_API_KEY=your-api-key-here          # Required: Google Gemini API
FLASK_SECRET_KEY=generate-random-string   # Required: Session encryption
PORT=3000                                  # Railway auto-set
FLASK_DEBUG=false                          # Production mode
```
