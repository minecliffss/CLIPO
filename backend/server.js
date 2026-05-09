const express = require("express");
const cors = require("cors");
const fs = require("fs");
const path = require("path");
const sizeOf = require("image-size");

const app = express();
const PORT = process.env.PORT || 3001;
const IMAGES_DIR = "/home/daniel/Desktop/Lensora/Images";

app.use(cors());
app.use(express.json());

// Serve images statically
app.use("/images", express.static(IMAGES_DIR));

// GET /api/images - list all images with dimensions
app.get("/api/images", (req, res) => {
  try {
    const files = fs.readdirSync(IMAGES_DIR);
    const imageFiles = files.filter((file) => {
      const ext = path.extname(file).toLowerCase();
      return [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"].includes(ext);
    });

    const images = imageFiles.map((file) => {
      const filePath = path.join(IMAGES_DIR, file);
      let width = 400;
      let height = 300;

      try {
        const dimensions = sizeOf(filePath);
        if (dimensions && dimensions.width && dimensions.height) {
          width = dimensions.width;
          height = dimensions.height;
        }
      } catch (e) {
        // fallback dimensions
      }

      return {
        name: file,
        src: `http://localhost:${PORT}/images/${encodeURIComponent(file)}`,
        alt: path.parse(file).name,
        width,
        height,
      };
    });

    res.json({ images });
  } catch (error) {
    console.error("Error reading images:", error);
    res.status(500).json({ error: "Failed to read images directory" });
  }
});

// Health check
app.get("/api/health", (req, res) => {
  res.json({ status: "ok" });
});

app.listen(PORT, () => {
  console.log(`Lensora backend running on http://localhost:${PORT}`);
});
