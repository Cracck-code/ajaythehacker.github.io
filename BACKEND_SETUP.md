# Istruzioni Backend

## Setup

1. Apri il terminale nella cartella `ItaVirtual`
2. Installa le dipendenze:
   ```
   npm install
   ```

3. Avvia il server:
   ```
   npm start
   ```

Il server girerà su `http://localhost:3000`

## API Endpoints

### Admin
- `POST /api/admin/login` - Login dell'admin
  ```json
  Body: { "password": "admin123" }
  Response: { "success": true, "token": "..." }
  ```

### Users (richiede autenticazione)
- `GET /api/users` - Ottenere tutti gli utenti
  - Header: `Authorization: Bearer <token>`
  
- `DELETE /api/users/:id` - Eliminare un utente
  - Header: `Authorization: Bearer <token>`

### Public Routes
- `POST /api/users/register` - Registrare un nuovo utente
  ```json
  Body: { "username": "...", "email": "...", "password": "..." }
  ```

- `POST /api/users/login` - Login dell'utente
  ```json
  Body: { "email": "...", "password": "..." }
  ```

## File Data
Gli utenti vengono salvati in `users.json` nella stessa cartella

## Sicurezza
⚠️ **Importante**: 
- Cambia `ADMIN_PASSWORD` in `server.js`
- Cambia `JWT_SECRET` in `server.js`
- In produzione, usa hash per le password (bcrypt)
- Usa HTTPS in produzione
