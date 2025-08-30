<div align="center">

# Iris - Open Source Generalist AI Agent

(that acts on your behalf)

![Iris Screenshot](frontend/public/banner.png)

Iris is a fully open source AI assistant that helps you accomplish real-world tasks with ease. Through natural conversation, Iris becomes your digital companion for research, data analysis, and everyday challenges—combining powerful capabilities with an intuitive interface that understands what you need and delivers results.

Iris's powerful toolkit includes seamless browser automation to navigate the web and extract data, file management for document creation and editing, web crawling and extended search capabilities, command-line execution for system tasks, website deployment, and integration with various APIs and services. These capabilities work together harmoniously, allowing Iris to solve your complex problems and automate workflows through simple conversations!

[![License](https://img.shields.io/badge/License-Apache--2.0-blue)](./license)
[![Discord Follow](https://dcbadge.limes.pink/api/server/Py6pCBUUPw?style=flat)](https://discord.gg/Py6pCBUUPw)
[![Twitter Follow](https://img.shields.io/twitter/follow/kortixai)](https://x.com/kortixai)
[![GitHub Repo stars](https://img.shields.io/github/stars/kortix-ai/iris)](https://github.com/kortix-ai/iris)
[![Issues](https://img.shields.io/github/issues/kortix-ai/iris
)](https://github.com/kortix-ai/iris/labels/bug)
</div>


## Table of Contents

- [Project Architecture](#project-architecture)
  - [Backend API](#backend-api)
  - [Frontend](#frontend)
  - [Agent Docker](#agent-docker)
  - [Supabase Database](#supabase-database)
- [Run Locally / Self-Hosting](#run-locally--self-hosting)
  - [Requirements](#requirements)
  - [Prerequisites](#prerequisites)
  - [Installation Steps](#installation-steps)
- [License](#license)

## Project Architecture

![Architecture Diagram](docs/images/diagram.png)

Iris consists of four main components:

### Backend API
Python/FastAPI service that handles REST endpoints, thread management, and LLM integration with OpenAI, Anthropic, and others via LiteLLM.

### Frontend
Next.js/React application providing a responsive UI with chat interface, dashboard, etc.

### Agent Docker
Isolated execution environment for every agent - with browser automation, code interpreter, file system access, tool integration, and security features.

### Supabase Database
Handles data persistence with authentication, user management, conversation history, file storage, agent state, analytics, and real-time subscriptions.

## Use Cases

Here are some examples of tasks that Iris can help you with:

1. **Competitor Analysis** – Analyze a market for your next business idea, identify key players, and produce a report with insights and links to their websites.
2. **Lead Generation** – Build a list of B2B leads in a specific industry and geography, including key contacts and company information.
3. **Research & Report Writing** – Summarize the latest scientific papers on a topic, compile data from multiple sources, and draft a professional report.
4. **Travel Planning** – Create a detailed itinerary for a trip based on dates, destinations, budget, and personal preferences, including accommodation and activities.
5. **Data Scraping & Analysis** – Scrape data from forums, e-commerce sites, or public databases, then cluster and analyze the results.
6. **Automation & Integration** – Automate workflows involving spreadsheets, APIs, and databases, connecting with your favorite tools to streamline repetitive tasks.

These are just a few ideas—because Iris is a generalist AI agent, you can ask it to perform a wide variety of tasks that involve research, data gathering, automation, and more.

## Run Locally / Self-Hosting

Iris can be self-hosted on your own infrastructure. Follow these steps to set up your own instance.

### Requirements

You'll need the following components:
- A Supabase project for database and authentication
- Redis database for caching and session management
- Daytona sandbox for secure agent execution
- Python 3.11 for the API backend
- API keys for LLM providers (OpenAI or Anthropic)
- (Optional but recommended) Tavily API key for enhanced search capabilities

### Prerequisites

1. **Supabase**: 
   - Create a new [Supabase project](https://supabase.com/dashboard/projects)
   - Save your project's API URL, anon key, and service role key for later use
   - Install the [Supabase CLI](https://supabase.com/docs/guides/cli/getting-started)

2. **Redis**: Set up a Redis instance using one of these options:
   - [Upstash Redis](https://upstash.com/) (recommended for cloud deployments)
   - Local installation:
     - [Mac](https://formulae.brew.sh/formula/redis): `brew install redis`
     - [Linux](https://redis.io/docs/getting-started/installation/install-redis-on-linux/): Follow distribution-specific instructions
     - [Windows](https://redis.io/docs/getting-started/installation/install-redis-on-windows/): Use WSL2 or Docker
   - Save your Redis connection details for later use

3. **Daytona**: 
   - Create an account on [Daytona](https://app.daytona.io/)
   - Generate an API key from your account settings
   - Go to [Images](https://app.daytona.io/dashboard/images)
   - Click "Add Image"
   - Enter `adamcohenhillel/kortix-iris:0.0.20` as the image name
   - Set `exec /usr/bin/supervisord -n -c /etc/supervisor/conf.d/supervisord.conf` as the Entrypoint

4. **LLM API Keys**:
   - Obtain an API key from [OpenAI](https://platform.openai.com/) or [Anthropic](https://www.anthropic.com/)
   - While other providers should work via [LiteLLM](https://github.com/BerriAI/litellm), OpenAI and Anthropic are recommended

5. **Search API Key** (Optional):
   - For enhanced search capabilities, obtain an [Tavily API key](https://tavily.com/)
  
6. **RapidAPI API Key** (Optional):
   - To enable API services like LinkedIn, and others, you'll need a RapidAPI key
   - Each service requires individual activation in your RapidAPI account:
     1. Locate the service's `base_url` in its corresponding file (e.g., `"https://linkedin-data-scraper.p.rapidapi.com"` in [`backend/agent/tools/data_providers/LinkedinProvider.py`](backend/agent/tools/data_providers/LinkedinProvider.py))
     2. Visit that specific API on the RapidAPI marketplace
     3. Subscribe to the service (many offer free tiers with limited requests)
     4. Once subscribed, the service will be available to your agent through the API Services tool

### Installation Steps

1. **Clone the repository**:
```bash
git clone https://github.com/kortix-ai/iris.git
cd iris
```

2. **Configure backend environment**:
```bash
cd backend
cp .env.example .env  # Create from example if available, or use the following template
```

Edit the `.env` file and fill in your credentials:
```bash
NEXT_PUBLIC_URL="http://localhost:3000"

# Supabase credentials from step 1
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key

# Redis credentials from step 2
REDIS_HOST=your_redis_host
REDIS_PORT=6379
REDIS_PASSWORD=your_redis_password
REDIS_SSL=True  # Set to False for local Redis without SSL

# Daytona credentials from step 3
DAYTONA_API_KEY=your_daytona_api_key
DAYTONA_SERVER_URL="https://app.daytona.io/api"
DAYTONA_TARGET="us"

# Anthropic or OpenAI: 
# Anthropic
ANTHROPIC_API_KEY=
MODEL_TO_USE="anthropic/claude-3-7-sonnet-latest"

# OR OpenAI API:
OPENAI_API_KEY=your_openai_api_key
MODEL_TO_USE="gpt-4o"

# Optional but recommended
TAVILY_API_KEY=your_tavily_api_key  # Optional
RAPID_API_KEY=
```

3. **Set up Supabase database**:
```bash
# Login to Supabase CLI
supabase login

# Link to your project (find your project reference in the Supabase dashboard)
supabase link --project-ref your_project_reference_id

# Push database migrations
supabase db push
```

4. **Configure frontend environment**:
```bash
cd ../frontend
cp .env.example .env.local  # Create from example if available, or use the following template
```

   Edit the `.env.local` file:
```
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
NEXT_PUBLIC_BACKEND_URL="http://localhost:8000/api"
NEXT_PUBLIC_URL="http://localhost:3000"
```

5. **Install dependencies**:
```bash
# Install frontend dependencies
cd frontend
npm install

# Install backend dependencies
cd ../backend
pip install -r requirements.txt
```

6. **Start the application**:

   In one terminal, start the frontend:
```bash
cd frontend
npm run dev
```

   In another terminal, start the backend:
```bash
cd backend
python app_main.py
```

7. **Access Iris**:
   - Open your browser and navigate to `http://localhost:3000`
   - Sign up for an account using the Supabase authentication
   - Start using your self-hosted Iris instance!

## License

Iris is licensed under the Apache License, Version 2.0. See [LICENSE](./LICENSE) for the full license text.
