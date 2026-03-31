const express = require('express');
const cors = require('cors');
const jwt = require('jsonwebtoken');
const fs = require('fs');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;
const ADMIN_PASSWORD = 'admin123'; // Cambia questa password!
const JWT_SECRET = 'your_secret_key_change_this'; // Cambia questa chiave segreta!

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.static(__dirname));

// File per salvare gli utenti
const USERS_FILE = path.join(__dirname, 'users.json');

// Funzione per leggere gli utenti dal file
function getUsers() {
    try {
        if (fs.existsSync(USERS_FILE)) {
            const data = fs.readFileSync(USERS_FILE, 'utf-8');
            return JSON.parse(data);
        }
    } catch (err) {
        console.error('Error reading users file:', err);
    }
    return [];
}

// Funzione per salvare gli utenti nel file
function saveUsers(users) {
    try {
        fs.writeFileSync(USERS_FILE, JSON.stringify(users, null, 2));
    } catch (err) {
        console.error('Error saving users file:', err);
    }
}

// Middleware per verificare il token JWT
function verifyToken(req, res, next) {
    const token = req.headers['authorization']?.split(' ')[1];
    
    if (!token) {
        return res.status(401).json({ success: false, message: 'No token provided' });
    }
    
    jwt.verify(token, JWT_SECRET, (err, decoded) => {
        if (err) {
            return res.status(401).json({ success: false, message: 'Invalid token' });
        }
        req.admin = decoded;
        next();
    });
}

// Rotta: Admin Login
app.post('/api/admin/login', (req, res) => {
    const { password } = req.body;
    
    if (password === ADMIN_PASSWORD) {
        const token = jwt.sign({ admin: true }, JWT_SECRET, { expiresIn: '24h' });
        res.json({ success: true, token });
    } else {
        res.status(401).json({ success: false, message: 'Incorrect password' });
    }
});

// Rotta: Ottenere tutti gli utenti (richiede auth)
app.get('/api/users', verifyToken, (req, res) => {
    const users = getUsers();
    res.json({ success: true, users });
});

// Rotta: Eliminare un utente (richiede auth)
app.delete('/api/users/:id', verifyToken, (req, res) => {
    const { id } = req.params;
    let users = getUsers();
    
    // Trova l'indice dell'utente
    const index = users.findIndex(u => u._id === id || u.id === id || users.indexOf(u) === parseInt(id));
    
    if (index === -1) {
        return res.status(404).json({ success: false, message: 'User not found' });
    }
    
    users.splice(index, 1);
    saveUsers(users);
    res.json({ success: true, message: 'User deleted' });
});

// Rotta: Registrare un nuovo utente (da usare dalle altre pagine)
app.post('/api/users/register', (req, res) => {
    const { username, email, password } = req.body;
    
    if (!username || !email || !password) {
        return res.status(400).json({ success: false, message: 'Missing fields' });
    }
    
    let users = getUsers();
    
    // Controlla se l'email esiste già
    if (users.find(u => u.email === email)) {
        return res.status(400).json({ success: false, message: 'Email already exists' });
    }
    
    // Aggiungi il nuovo utente
    const newUser = {
        _id: Date.now().toString(),
        username,
        email,
        password // In produzione, hashare la password!
    };
    
    users.push(newUser);
    saveUsers(users);
    
    res.status(201).json({ success: true, message: 'User registered', user: newUser });
});

// Rotta: Login utente (da usare dalle altre pagine)
app.post('/api/users/login', (req, res) => {
    const { email, password } = req.body;
    
    const users = getUsers();
    const user = users.find(u => u.email === email && u.password === password);
    
    if (!user) {
        return res.status(401).json({ success: false, message: 'Invalid credentials' });
    }
    
    res.json({ success: true, message: 'Logged in', user });
});

// Avvia il server
const server = app.listen(PORT, () => {
    console.log(`Server running on http://localhost:${PORT}`);
    console.log('API endpoints:');
    console.log('  POST /api/admin/login - Admin login');
    console.log('  GET /api/users - Get all users (requires auth)');
    console.log('  DELETE /api/users/:id - Delete user (requires auth)');
    console.log('  POST /api/users/register - Register new user');
    console.log('  POST /api/users/login - Login user');
});

server.on('error', (err) => {
    if (err.code === 'EADDRINUSE') {
        console.error(`Port ${PORT} is already in use. Use another port: set PORT=<number> and restart.`);
    } else {
        console.error('Server error:', err);
    }
    process.exit(1);
});
