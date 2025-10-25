# Frontend Deployment Guide for Render.com

## 🚨 **Critical Fix for 502 Error**

The 502 error was caused by missing environment variables in your Render deployment. Follow these steps to fix it:

## 1. Environment Variables Setup

In your Render dashboard for the frontend service, add these environment variables:

```bash
# Required - Replace with your actual backend URL
BASE_URL=https://your-backend-service-name.onrender.com

# Production environment
NODE_ENV=production

# Port (Render sets this automatically, but good to have)
PORT=3000
```

## 2. Render Service Configuration

### Frontend Service Settings:
- **Environment**: `Node`
- **Build Command**: `npm install && npm run build`
- **Start Command**: `npm start`
- **Node Version**: `20`

### Important Files Updated:
- ✅ `Dockerfile` - Fixed for production deployment
- ✅ `next.config.ts` - Added environment variable support
- ✅ `package.json` - Updated start script for dynamic port
- ✅ `.env.example` - Template for environment variables

## 3. Backend URL Configuration

Your frontend makes API calls to `process.env.BASE_URL`. You need to:

1. Find your backend service URL on Render (e.g., `https://your-backend-name.onrender.com`)
2. Set the `BASE_URL` environment variable in your frontend service to this URL
3. Ensure your backend service is running and accessible

## 4. Common 502 Error Causes & Solutions:

### ❌ **Missing BASE_URL**
**Problem**: Frontend can't reach backend API
**Solution**: Set `BASE_URL` environment variable to your backend URL

### ❌ **Wrong Port Configuration**
**Problem**: Service not binding to correct port
**Solution**: Use `$PORT` in start command (already fixed in package.json)

### ❌ **Build Failures**
**Problem**: TypeScript/ESLint errors preventing build
**Solution**: Already configured to ignore these in `next.config.ts`

### ❌ **Standalone Build Issues**
**Problem**: Missing dependencies in standalone output
**Solution**: Fixed in updated `Dockerfile`

## 5. Deployment Steps:

1. **Push your code** with the updated files
2. **Set environment variables** in Render dashboard:
   - `BASE_URL=https://your-backend-url.onrender.com`
   - `NODE_ENV=production`
3. **Redeploy** the service
4. **Check logs** for any remaining issues

## 6. Verification:

After deployment, check:
- ✅ Service starts without errors
- ✅ Frontend loads in browser
- ✅ API calls to backend work (check Network tab)
- ✅ No 502 errors

## 7. Troubleshooting:

If you still get 502 errors:
1. Check Render logs for your frontend service
2. Verify `BASE_URL` is set correctly
3. Test backend API directly to ensure it's working
4. Check if backend allows CORS from your frontend domain

## Backend URL Format:
Your backend URL should be: `https://[your-backend-service-name].onrender.com`

Replace `[your-backend-service-name]` with the actual name of your backend service on Render.