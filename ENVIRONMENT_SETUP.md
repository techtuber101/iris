# 🌍 Iris AI Environment Configuration System

## Overview
This system allows you to easily switch between **local development** and **production** environments with just one command. All environment variables are centrally managed and automatically distributed to the appropriate files.

## 🚀 Quick Start

### Switch to Production (for deployment):
```bash
./switch-env.sh production
```

### Switch to Local (for development):
```bash
./switch-env.sh local
```

### Check current environment:
```bash
./switch-env.sh status
```

## 📁 File Structure

```
iris-clean7 10/
├── env.config.master          # Master configuration file (edit this)
├── generate-env.py            # Environment generator script
├── switch-env.sh              # Environment switcher script
├── .env                       # Root environment (auto-generated)
├── backend/
│   └── .env                  # Backend environment (auto-generated)
└── frontend/
    └── .env.local            # Frontend environment (auto-generated)
```

## 🔧 How It Works

1. **`env.config.master`** - Contains ALL environment variables
2. **`generate-env.py`** - Reads master config and generates appropriate .env files
3. **`switch-env.sh`** - Changes ENV_MODE and regenerates files

## 📋 Environment Variables Included

### 🔐 Authentication & Database
- `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`
- `REDIS_HOST`, `REDIS_PORT`

### 🤖 AI & LLM
- `GEMINI_API_KEY`, `MODEL_TO_USE`
- `MORPH_API_KEY`, `TAVILY_API_KEY`, `FIRECRAWL_API_KEY`

### 🔌 Integrations
- `QSTASH_URL`, `QSTASH_TOKEN`
- `SLACK_CLIENT_ID`, `SLACK_CLIENT_SECRET`
- `PIPEDREAM_PROJECT_ID`, `PIPEDREAM_CLIENT_ID`
- `DAYTONA_API_KEY`, `DAYTONA_SERVER_URL`
- `KORTIX_ADMIN_API_KEY`

### 🌐 Frontend Configuration
- `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- `NEXT_PUBLIC_BACKEND_URL`, `NEXT_PUBLIC_URL`
- `NEXT_PUBLIC_ENV_MODE`

### 🔒 Security & CORS
- `MCP_CREDENTIAL_ENCRYPTION_KEY`
- `CORS_ORIGINS` (automatically set based on environment)

## 🌍 Environment-Specific Settings

### Local Development (`ENV_MODE=local`)
- **Frontend**: `http://localhost:3000`
- **Backend**: `http://localhost:8000`
- **CORS**: `http://localhost:3000`

### Production (`ENV_MODE=production`)
- **Frontend**: `https://irisvision.ai`
- **Backend**: `https://irisvision.ai/api`
- **CORS**: `https://irisvision.ai, https://www.irisvision.ai`

## 🛠️ Usage Examples

### 1. Deploy to Production
```bash
# Switch to production mode
./switch-env.sh production

# Verify the change
./switch-env.sh status

# Deploy your application
# (Your deployment script will use the production URLs)
```

### 2. Switch Back to Development
```bash
# Switch to local mode
./switch-env.sh local

# Verify the change
./switch-env.sh status

# Start local development
docker-compose up
```

### 3. Manual Environment Generation
```bash
# Edit env.config.master manually
# Change ENV_MODE to 'local' or 'production'

# Generate environment files
python3 generate-env.py
```

## 🔍 Verification

After switching environments, verify the changes:

### Check Frontend URLs:
```bash
grep "NEXT_PUBLIC_URL" frontend/.env.local
grep "NEXT_PUBLIC_BACKEND_URL" frontend/.env.local
```

### Check Backend CORS:
```bash
grep "CORS_ORIGINS" backend/.env
```

### Check Environment Mode:
```bash
grep "ENV_MODE" backend/.env
grep "NEXT_PUBLIC_ENV_MODE" frontend/.env.local
```

## 🚨 Important Notes

1. **Never edit generated .env files directly** - they will be overwritten
2. **Always edit `env.config.master`** for configuration changes
3. **Run `./switch-env.sh` after editing** to apply changes
4. **All variables are preserved** when switching environments
5. **CORS and URLs are automatically updated** based on environment

## 🔄 Adding New Variables

To add a new environment variable:

1. **Add it to `env.config.master`**:
   ```bash
   # Add your new variable
   NEW_VARIABLE=your_value_here
   ```

2. **Update `generate-env.py`** if needed (for environment-specific logic)

3. **Regenerate environment files**:
   ```bash
   python3 generate-env.py
   ```

## 🐛 Troubleshooting

### Issue: URLs not updating
- Check that `ENV_MODE` in `env.config.master` doesn't have comments
- Ensure the file format is correct (no extra spaces)

### Issue: Variables missing
- Verify the variable exists in `env.config.master`
- Check that `generate-env.py` includes it in the appropriate section

### Issue: Permission denied
- Make scripts executable: `chmod +x switch-env.sh`
- Ensure Python is available: `python3 --version`

## 🎯 Production Deployment Checklist

Before deploying to production:

1. ✅ **Switch to production mode**: `./switch-env.sh production`
2. ✅ **Verify URLs**: Check that all URLs point to `irisvision.ai`
3. ✅ **Verify CORS**: Ensure CORS allows `irisvision.ai` domains
4. ✅ **Check environment mode**: Confirm `ENV_MODE=production`
5. ✅ **Test locally**: Ensure production config works in local testing
6. ✅ **Deploy**: Use your deployment script

## 📞 Support

If you encounter issues:

1. Check the current environment: `./switch-env.sh status`
2. Verify file permissions: `ls -la switch-env.sh generate-env.py`
3. Check Python installation: `python3 --version`
4. Review the generated .env files for any obvious issues

---

**🎉 You're now ready to deploy with a perfectly configured environment system!**
