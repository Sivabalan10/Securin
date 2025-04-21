# Recipe API By Sivabalan T

## Verify the Documents for Detailed Explannation
- [Docs Link](https://docs.google.com/document/d/16gV7EQck6rJ89sC9ex_zftPFtToo2ZpfVzUy15VrObw/edit?usp=sharing)
  
##  Project Structure
```
recipe-app/
├── backend/
│   └── app.py
├── frontend/
│   └── react-host-html/
│       ├── package.json
│       └── ...
```

## Prerequisites

### 1. Install PostgreSQL
- Install PostgreSQL from the official site or use your package manager.
- Open pgAdmin4 and create a new database named `receipe_db`.
- Set up credentials accordingly and update the `.env` file:
```env
DATABASE_URL='postgresql://postgres:password@localhost/receipe_db'
```

### 2. Setup Redis Server

#### On Linux:
```bash
sudo apt update
sudo apt install redis-server
sudo systemctl enable redis-server.service
sudo systemctl start redis-server
```

#### On Windows using Docker:
- Make sure Docker is installed and running.
```bash
docker run --name redis-dev -p 6379:6379 -d redis
```
To start the Redis server if it's stopped:
```bash
docker start redis-dev
```

---

## 🚀 Backend Setup
```bash
cd backend
```
### To create the database and store recipe data:
```bash
pip install -r requirements.txt
```
```bash
python app.py
```
- After the server is running, visit:
```
http://localhost:5000/load_data
```
This will load the recipe data into the PostgreSQL database.

### API Endpoints:
- Swagger Documentation: `http://localhost:5000/apidocs`
- Get All Recipes: `http://localhost:5000/api/recipes`
- Search Recipes: `http://localhost:5000/api/recipes/search?query=dosa`

---

## 🌐 Frontend Setup
```bash
cd frontend
cd react-host-html
```
### To install dependencies and run:
```bash
npm install
npm start
```
- The frontend will start at `http://localhost:3000`

---

## 🧪 Testing Redis Cache (To Evaluate Performance)
- Use Postman to test the `/api/recipes/search` endpoint.
- First request: data is fetched from PostgreSQL and cached.
- Second request: same query returns data faster from Redis.

---





