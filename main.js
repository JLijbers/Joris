const { app, BrowserWindow } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const http = require('http');

let mainWindow;
let flaskProcess;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 800,
    height: 600,
    webPreferences: {
      nodeIntegration: true
    }
  });

  mainWindow.loadURL('http://localhost:5000');

  mainWindow.on('closed', function () {
    mainWindow = null;
  });
}

function startFlaskServer() {
  const condaPythonPath = path.join(process.env.CONDA_PREFIX, 'python.exe');
  flaskProcess = spawn(condaPythonPath, [path.join(__dirname, 'flask_app', 'main.py')]);
  
  flaskProcess.stdout.on('data', (data) => {
    console.log(`Flask: ${data}`);
  });

  flaskProcess.stderr.on('data', (data) => {
    console.error(`Flask: ${data}`);
  });
}

app.on('ready', () => {
  startFlaskServer();
  createWindow();
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('quit', () => {
  if (flaskProcess) {
    flaskProcess.kill();
  }
});