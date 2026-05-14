const express = require("express");
const cors = require("cors");
const fs = require("fs");
const path = require("path");

const app = express();
const PORT = process.env.PORT || 3001;
const IMAGES_DIR = process.env.IMAGES_DIR || "/home/daniel/Desktop/AI Gallery/Images";

app.use(cors());

app.use("/images", express.static(IMAGES_DIR));

app.get("/api/images", (req, res) => {
  try {
    if (!fs.existsSync(IMAGES_DIR)) {
      return res.json({ images: [] });
    }
    
    const files = fs.readdirSync(IMAGES_DIR);
    const imageFiles = files.filter((file) => {
      const ext = path.extname(file).toLowerCase();
      return [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"].includes(ext);
    });

    const images = imageFiles.map((file) => {
      return {
        name: file,
        src: `/images/${encodeURIComponent(file)}`,
        alt: path.parse(file).name,
        width: 400,
        height: 300,
      };
    });

    res.json({ images });
  } catch (error) {
    console.error("Error reading images:", error);
    res.json({ images: [] });
  }
});

app.get("/api/health", (req, res) => {
  res.json({ status: "ok", mode: "static-server" });
});

app.listen(PORT, () => {
  console.log(`CLIPO static server running on http://localhost:${PORT}`);
  console.log(`Serving images from: ${IMAGES_DIR}`);
});