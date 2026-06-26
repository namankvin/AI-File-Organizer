const { app, BrowserWindow } = require("electron");

function createWindow() {
  const win = new BrowserWindow({
    width: 1400,
    height: 900,
    backgroundColor: "#0f1117",
  });

  win.loadURL("http://localhost:5173");
}

app.whenReady().then(createWindow);